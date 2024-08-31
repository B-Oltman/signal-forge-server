from pymongo import MongoClient, ASCENDING
from datetime import datetime
from typing import List, Optional
from .models import Parameter, ParameterValue, ParameterGroup, Session, TradeStatistics, TradingSystem

client = MongoClient('mongodb://localhost:27017/')
db = client['trading_systems']

def create_indexes():
    db.parameters.create_index([('key', ASCENDING), ('tradeSystemName', ASCENDING)], unique=True)
    db.parameter_groups.create_index([('id', ASCENDING), ('tradeSystemName', ASCENDING)], unique=True)
    db.sessions.create_index([('id', ASCENDING)], unique=True)
    db.sessions.create_index([('parameterGroupId', ASCENDING)])
    db.trading_systems.create_index([('name', ASCENDING)], unique=True)

create_indexes()
        
def preprocess_parameter(param):
    return {
        **param,
        "minValue": None if param.get("minValue") == "" else param.get("minValue"),
        "maxValue": None if param.get("maxValue") == "" else param.get("maxValue"),
        "options": param.get("options", []) if isinstance(param.get("options"), list) else param.get("options").split(",") if param.get("options") else []
    }

def get_parameters(trade_system_name: str) -> List[Parameter]:
    parameters = []
    for param in db.parameters.find({"tradeSystemName": trade_system_name}, {'_id': 0}):
        preprocessed_param = preprocess_parameter(param)
        parameters.append(Parameter(**preprocessed_param))
    return parameters

def insert_parameter_groups(parameter_groups: List[dict]):
    for group in parameter_groups:
        # Convert to dictionary only if necessary
        group_dict = group if isinstance(group, dict) else group.dict()
        
        group_dict['_id'] = f"{group_dict['tradeSystemName']}_{group_dict['id']}"  # Ensure ID is correctly formatted
        
        # Save only the values of the parameters
        parameter_values = {key: {'value': param['value']} for key, param in group_dict['parameters'].items()}
        group_dict['parameters'] = parameter_values
        
        db.parameter_groups.replace_one({'_id': group_dict['_id']}, group_dict, upsert=True)


def get_parameter_groups(trade_system_name: str, group_id: Optional[str] = None) -> List[ParameterGroup]:
    if not group_id:
        latest_group = db.parameter_groups.find_one(
            {'tradeSystemName': trade_system_name},
            sort=[('lastUpdated', -1)]
        )
        if latest_group:
            group_id = latest_group['id']
    
    return [ParameterGroup(**group) for group in db.parameter_groups.find({"tradeSystemName": trade_system_name, "id": group_id}, {'_id': 0})]

def insert_session(session: Session):
    session_dict = session.dict()  # Use dict()
    session_dict['_id'] = str(session_dict.pop('id'))  # Ensure ID is a string
    
    # Upsert the session
    db.sessions.replace_one({'_id': session_dict['_id']}, session_dict, upsert=True)

def get_sessions() -> List[Session]:
    return [Session(**session) for session in db.sessions.find({}, {'_id': 0})]

def get_sessions_by_date(start_date: datetime, end_date: datetime) -> List[Session]:
    return [Session(**session) for session in db.sessions.find({'startDate': {'$gte': start_date}, 'endDate': {'$lte': end_date}}, {'_id': 0})]

def get_statistics(session_id: str) -> Optional[TradeStatistics]:
    session = db.sessions.find_one({'id': session_id}, {'tradeStatistics': 1, '_id': 0})
    if session and 'tradeStatistics' in session:
        return TradeStatistics(**session['tradeStatistics'])
    return None

def insert_trading_system(trading_system_dict):
    trading_system_dict['_id'] = trading_system_dict['name']
    # Convert nested objects to dictionaries
    if trading_system_dict.get('sessionSettings'):
        trading_system_dict['sessionSettings'] = trading_system_dict['sessionSettings'].dict()
    if trading_system_dict.get('systemSettings'):
        trading_system_dict['systemSettings'] = trading_system_dict['systemSettings'].dict()
    if trading_system_dict.get('dataProcessingServer'):
        trading_system_dict['dataProcessingServer'] = trading_system_dict['dataProcessingServer'].dict()

    db.trading_systems.replace_one({'_id': trading_system_dict['_id']}, trading_system_dict, upsert=True)

def get_trading_systems(trading_system_name: Optional[str] = None) -> List[TradingSystem]:
    if trading_system_name:
        systems = db.trading_systems.find({"name": trading_system_name})
    else:
        systems = db.trading_systems.find()
    
    return [TradingSystem(**system) for system in systems]


def fetch_complete_parameter_group(trade_system_name: str, group_id: str, include_metadata: bool = False) -> dict:
    # Initialize parameter values
    parameter_values = {}

    # Fetch the parameter group from the `parameter_groups` collection
    parameter_group = db.parameter_groups.find_one({"tradeSystemName": trade_system_name, "id": group_id}, {'_id': 0})
    
    if include_metadata:
        # Fetch parameter metadata from the `parameters` collection
        parameters_metadata = {}
        for param in db.parameters.find({"tradeSystemName": trade_system_name}):
            # Handle empty strings for minValue, maxValue, and options
            param['minValue'] = None if param.get('minValue') == '' else param.get('minValue')
            param['maxValue'] = None if param.get('maxValue') == '' else param.get('maxValue')
            param['options'] = param.get('options', []) if isinstance(param.get('options'), list) else param.get('options').split(",") if param.get('options') else []
            
            parameters_metadata[param['key']] = Parameter(**param)

        if parameter_group:
            # Merge metadata and values
            for key, metadata in parameters_metadata.items():
                if key in parameter_group['parameters']:
                    value = parameter_group['parameters'][key]['value']
                    parameter_values[key] = ParameterValue(**metadata.dict(), value=value)
                else:
                    parameter_values[key] = ParameterValue(**metadata.dict(), value=metadata.default)
        else:
            # If no group exists, initialize with defaults
            for key, metadata in parameters_metadata.items():
                parameter_values[key] = ParameterValue(**metadata.dict(), value=metadata.default)
    else:
        if parameter_group:
            # Only use the parameter values without metadata
            for key, value in parameter_group['parameters'].items():
                parameter_values[key] = {"value": value['value']}

    # Create a complete parameter group with or without metadata based on include_metadata
    complete_parameter_group = {
        "tradeSystemName": trade_system_name,
        "id": group_id,
        "lastUpdated": datetime.utcnow(),
        "parameters": {key: value.dict() if include_metadata else value for key, value in parameter_values.items()}
    }
    
    return complete_parameter_group


def delete_parameter(key: str, trade_system_name: str):
    db.parameters.delete_one({'_id': key, 'tradeSystemName': trade_system_name})
    
def insert_parameters(parameters: List[dict]):
    for param in parameters:
        if isinstance(param, dict):
            param_dict = param
        else:
            param_dict = param.dict()

        # Use `key` as the unique identifier (_id)
        param_dict['_id'] = param_dict['key']
        db.parameters.replace_one({'_id': param_dict['_id']}, param_dict, upsert=True)

def update_parameter(parameter: dict):
    updated_key = parameter.get('key')
    old_key = parameter.get('updatedKey')
    trade_system_name = parameter.get('tradeSystemName')

    if updated_key and trade_system_name:
        # Find the existing document using the old key
        existing_parameter = db.parameters.find_one(
            {'_id': old_key, 'tradeSystemName': trade_system_name}
        )
        
        if existing_parameter:
            # Remove the old document
            db.parameters.delete_one({'_id': old_key, 'tradeSystemName': trade_system_name})
            
            # Insert the new document with the updated key as _id
            parameter['_id'] = updated_key  # Set the new _id
            parameter['updatedKey'] = None  # Remove the updatedKey field
            db.parameters.insert_one(parameter)
        else:
            raise ValueError("No existing parameter found to update.")
    else:
        raise ValueError("Key and TradeSystemName are required to update a parameter.")
    
def update_related_collections(old_name, new_name):
    db.parameter_groups.update_many({'tradeSystemName': old_name}, {'$set': {'tradeSystemName': new_name}})
    db.parameters.update_many({'tradeSystemName': old_name}, {'$set': {'tradeSystemName': new_name}})
    db.sessions.update_many({'tradeSystemName': old_name}, {'$set': {'tradeSystemName': new_name}})

def delete_trading_system_by_name(name):
    db.trading_systems.delete_one({'_id': name})

def upsert_trading_system(trading_system_dict):
    # Convert enum fields to their integer representations
    if 'sessionSettings' in trading_system_dict:
        if 'updateIntervalType' in trading_system_dict['sessionSettings']:
            trading_system_dict['sessionSettings']['updateIntervalType'] = trading_system_dict['sessionSettings']['updateIntervalType'].value
    
    db.trading_systems.replace_one({'_id': trading_system_dict['_id']}, trading_system_dict, upsert=True)

    
def update_related_collections(old_name, new_name):
    db.parameter_groups.update_many({'tradeSystemName': old_name}, {'$set': {'tradeSystemName': new_name}})
    db.parameters.update_many({'tradeSystemName': old_name}, {'$set': {'tradeSystemName': new_name}})
    db.sessions.update_many({'tradeSystemName': old_name}, {'$set': {'tradeSystemName': new_name}})

def delete_trading_system_by_name(name):
    db.trading_systems.delete_one({'_id': name})

def update_parameter_and_related_groups(old_key, new_key, trade_system_name, updateParameter):
    # Find the parameter in the `parameters` collection
    parameter = db.parameters.find_one({'_id': old_key, 'tradeSystemName': trade_system_name})
    
    if not parameter:
        raise ValueError("No existing parameter found to update.")
    
    # Check if the key is changing
    if old_key != new_key:
        # If the key is changing, delete the old document
        db.parameters.delete_one({'_id': old_key, 'tradeSystemName': trade_system_name})
        
        # Update the parameter document with the new key
        updateParameter['_id'] = new_key
        updateParameter['key'] = new_key
        
        # Insert the updated parameter
        db.parameters.insert_one(updateParameter)

        # Update related parameter_groups with the new key
        db.parameter_groups.update_many(
            {'tradeSystemName': trade_system_name, f'parameters.{old_key}': {'$exists': True}},
            {'$rename': {f'parameters.{old_key}': f'parameters.{new_key}'}}
        )
    else:
        # If the key is not changing, we can directly update the existing document
        db.parameters.update_one(
            {'_id': old_key, 'tradeSystemName': trade_system_name},  # Filter by the existing key and trade system name
            {'$set': updateParameter}  # Apply the updates
        )
    
    # Apply any additional updates to the new (or existing) document
    if old_key == new_key:
        db.parameters.update_one(
            {'_id': new_key, 'tradeSystemName': trade_system_name},  # Filter by the new key and trade system name
            {'$set': updateParameter}  # Apply the updates
        )







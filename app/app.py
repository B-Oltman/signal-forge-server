from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import requests
from pymongo import MongoClient
from config import CPPServerConfig
from .tasks import start_background_task
from .database import (
    insert_parameters,
    get_parameters,
    insert_parameter_groups,
    get_parameter_groups,
    get_statistics,
    delete_parameter,
    update_parameter,
    get_trading_systems,
    insert_trading_system,
    insert_session,
    get_sessions,
    get_sessions_by_date,
    fetch_complete_parameter_group,
    update_related_collections,
    delete_trading_system_by_name,
    upsert_trading_system,
    update_parameter_and_related_groups
)
from .models import Session, TradingSystem

app = Flask(__name__)
CORS(app)
client = MongoClient('mongodb://localhost:27017/')
db = client['trading_systems']

def parse_date(date_str):
    return datetime.strptime(date_str.strip(), '%a %b %d %H:%M:%S %Y')

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/insert-parameter', methods=['POST'])
def insert_parameter_route():
    parameter = request.json
    insert_parameters([parameter])  # Use the database function
    return jsonify({"message": "Parameter metadata inserted successfully"}), 200

@app.route('/insert-parameter-group', methods=['POST'])
def insert_parameter_group_route():
    parameter_group = request.json
    parameter_group['lastUpdated'] = datetime.utcnow()
    
    # Check if the updatedId field is provided for updating the Group ID
    updated_id = parameter_group.get('updatedId')
    
    if updated_id:
        # Delete the old group with the original ID
        db.parameter_groups.delete_one({'id': parameter_group['id'], 'tradeSystemName': parameter_group['tradeSystemName']})
        parameter_group['id'] = updated_id  # Use the updated ID
    
    # Ensure a unique id is generated if not provided
    if 'id' not in parameter_group:
        parameter_group['id'] = str(datetime.utcnow().timestamp()).replace('.', '')
    
    insert_parameter_groups([parameter_group])  # Use the database function
    
     # Notify the C++ server
    payload = {
        "tradeSystemName": parameter_group['tradeSystemName'],
        "groupId": parameter_group['id']
    }
    try:
        response = requests.post(f'http://{CPPServerConfig.CPP_SERVER_HOST}:{CPPServerConfig.CPP_SERVER_PORT}/update-parameter-group', json=payload)
        print(f"C++ Server Response: {response.status_code} - {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error notifying C++ server: {e}")
    
    return jsonify({"message": "Parameter group inserted successfully", "id": parameter_group['id']}), 200


@app.route('/get-parameters', methods=['GET'])
def get_parameters_route():
    trade_system_name = request.args.get('tradeSystemName')
    parameters = get_parameters(trade_system_name)  # Use the database function
    parameters_dict = [param.dict() for param in parameters]  # Convert Parameter objects to dicts
    return jsonify(parameters_dict), 200

@app.route('/get-parameter-groups', methods=['GET'])
def get_parameter_groups_route():
    trade_system_name = request.args.get('tradeSystemName')
    group_id = request.args.get('groupId')
    include_metadata = request.args.get('includeMetadata', 'false').lower() == 'true'

    if group_id == 'latest':
        # Fetch the latest parameter group
        latest_group = db.parameter_groups.find_one(
            {'tradeSystemName': trade_system_name},
            sort=[('lastUpdated', -1)]
        )
        if latest_group:
            if include_metadata:
                parameter_group = fetch_complete_parameter_group(trade_system_name, latest_group['id'], include_metadata=True)
                return jsonify(parameter_group), 200
            return jsonify(latest_group), 200
        else:
            return jsonify({"error": "No parameter groups found for this trading system."}), 404
    
    elif group_id:
        # Fetch a specific parameter group by ID
        parameter_group = fetch_complete_parameter_group(trade_system_name, group_id, include_metadata=include_metadata)
        if parameter_group:
            if include_metadata:
                return jsonify(parameter_group), 200
            else:
                # Send only parameter values without metadata
                return jsonify({
                    "id": parameter_group["id"],
                    "tradeSystemName": parameter_group["tradeSystemName"],
                    "lastUpdated": parameter_group["lastUpdated"],
                    "parameters": {key: {"value": value["value"]} for key, value in parameter_group["parameters"].items()}
                }), 200
        else:
            return jsonify({"error": f"No parameter group found with id {group_id}."}), 404
    
    else:
        # Fetch all parameter groups for the trading system
        parameter_groups = db.parameter_groups.find({"tradeSystemName": trade_system_name}, {'_id': 0})
        parameter_groups_list = []

        if include_metadata:
            for group in parameter_groups:
                complete_group = fetch_complete_parameter_group(trade_system_name, group['id'], include_metadata=True)
                parameter_groups_list.append(complete_group)
        else:
            parameter_groups_list = [group for group in parameter_groups]

        return jsonify(parameter_groups_list), 200

    
@app.route('/delete-parameter-group', methods=['DELETE'])
def delete_parameter_group_route():
    data = request.json
    group_id = data.get('id')
    trade_system_name = data.get('tradeSystemName')
    
    if not group_id or not trade_system_name:
        return jsonify({"error": "Group ID and TradeSystemName are required"}), 400
    
    db.parameter_groups.delete_one({'id': group_id, 'tradeSystemName': trade_system_name})
    return jsonify({"message": "Parameter group deleted successfully"}), 200



@app.route('/insert-session', methods=['POST'])
def insert_session_route():
    session_dict = request.json
    session_dict['startDate'] = parse_date(session_dict['startDate'])
    session_dict['endDate'] = parse_date(session_dict['endDate'])
    session_dict['tradeStatistics']['lastEntryDateTime'] = parse_date(session_dict['tradeStatistics']['lastEntryDateTime'])
    session_dict['tradeStatistics']['lastExitDateTime'] = parse_date(session_dict['tradeStatistics']['lastExitDateTime'])
    session_dict['tradeStatistics']['lastFillDateTime'] = parse_date(session_dict['tradeStatistics']['lastFillDateTime'])
    session_dict['tradeStatistics']['sessionEndDateTime'] = parse_date(session_dict['tradeStatistics']['sessionEndDateTime'])
    session_dict['_id'] = session_dict['id']
    
    # Ensure the parameterGroupId is correctly set
    if 'parameterGroupId' not in session_dict or session_dict['parameterGroupId'] == '':  # Check if the parameterGroupId is missing
        return jsonify({"error": "parameterGroupId is required"}), 400
    
    # Convert the dictionary to a Session object
    session = Session(**session_dict)
    
    insert_session(session)  # Use the database function
    return jsonify({"message": "Session inserted successfully"}), 200

@app.route('/get-sessions', methods=['GET'])
def get_sessions_route():
    sessions = get_sessions()  # Use the database function
    return jsonify(sessions), 200

@app.route('/get-sessions-by-date', methods=['GET'])
def get_sessions_by_date_route():
    start_date = parse_date(request.args.get('start_date'))
    end_date = parse_date(request.args.get('end_date'))
    sessions = get_sessions_by_date(start_date, end_date)  # Use the database function
    return jsonify(sessions), 200

@app.route('/add-trading-system', methods=['POST'])
def add_trading_system_route():
    data = request.json

    # Ensure 'barPeriod' is handled as a string
    if 'sessionSettings' in data:
        if 'barPeriod' not in data['sessionSettings'] or not isinstance(data['sessionSettings']['barPeriod'], str):
            data['sessionSettings']['barPeriod'] = '1'  # Default value as string

        if isinstance(data['sessionSettings']['updateIntervalType'], str):
            data['sessionSettings']['updateIntervalType'] = 0 if data['sessionSettings']['updateIntervalType'] == "New_Bar" else 1

    updated_name = data.get('updatedName')

    if updated_name and updated_name != data['name']:
        update_related_collections(data['name'], updated_name)
        delete_trading_system_by_name(data['name'])

    # Construct the TradingSystem object
    trading_system = TradingSystem(**data)
    trading_system_dict = trading_system.dict()

    if updated_name:
        trading_system_dict['name'] = updated_name

    trading_system_dict['_id'] = trading_system_dict['name']  # Use name as _id

    upsert_trading_system(trading_system_dict)
    
        # Notify the C++ server
    payload = {
        "tradeSystemName": data['name']
    }
    try:
        response = requests.post(f'http://{CPPServerConfig.CPP_SERVER_HOST}:{CPPServerConfig.CPP_SERVER_PORT}/update-trading-system', json=payload)
        print(f"C++ Server Response: {response.status_code} - {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error notifying C++ server: {e}")

    return jsonify({"message": "Trading system added/updated successfully", "id": trading_system_dict['_id']}), 200



@app.route('/delete-trading-system', methods=['DELETE'])
def delete_trading_system_route():
    data = request.json
    name = data.get('name')

    if not name:
        return jsonify({"error": "Name is required to delete a trading system"}), 400
    
    # Delete the trading system by name
    db.trading_systems.delete_one({'_id': name})
    
    # Optionally, you can also delete related parameter groups, parameters, and sessions
    db.parameter_groups.delete_many({'tradeSystemName': name})
    db.parameters.delete_many({'tradeSystemName': name})
    db.sessions.delete_many({'tradeSystemName': name})
    
    return jsonify({"message": f"Trading system '{name}' deleted successfully"}), 200


@app.route('/get-trading-systems', methods=['GET'])
def get_trading_systems_route():
    trading_system_name = request.args.get('tradeSystemName')
    trading_systems = get_trading_systems(trading_system_name)

    def convert_to_serializable(system):
        system_dict = system.dict()
        # Convert enum fields to their int representations
        if 'sessionSettings' in system_dict:
            if 'updateIntervalType' in system_dict['sessionSettings']:
                system_dict['sessionSettings']['updateIntervalType'] = system_dict['sessionSettings']['updateIntervalType'].value
        return system_dict

    serializable_systems = [convert_to_serializable(system) for system in trading_systems]

    return jsonify(serializable_systems), 200


@app.route('/delete-parameter', methods=['DELETE'])
def delete_parameter_route():
    data = request.json
    key = data.get('key')
    trade_system_name = data.get('tradeSystemName')
    
    if not key or not trade_system_name:
        return jsonify({"error": "Key and TradeSystemName are required"}), 400
    
    delete_parameter(key, trade_system_name)
    return jsonify({"message": "Parameter deleted successfully"}), 200

@app.route('/update-parameter', methods=['PUT'])
def update_parameter_route():
    parameter = request.json
    
    old_key = parameter.get('updatedKey')
    new_key = parameter.get('key')
    trade_system_name = parameter.get('tradeSystemName')

    try:
        if old_key and trade_system_name:
            update_parameter_and_related_groups(old_key, new_key, trade_system_name, parameter)
        else:
            raise ValueError("Key and TradeSystemName are required to update a parameter.")
        
        return jsonify({"message": "Parameter and related groups updated successfully"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400




# Start the background task when the app starts
start_background_task()

if __name__ == '__main__':
    app.run(debug=True)

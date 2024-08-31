# Parameter Tuner Server

This project contains a Flask server for tuning parameters using a machine learning model.

## Setup

1. Install dependencies:

    ```sh
    pip install -r requirements.txt
    ```

2. Run the server:

    ```sh
    python server.py
    ```

## Endpoints

### `/receive-data`

- **Method**: POST
- **Description**: Receives data and logs it.
- **Request Body**: JSON

### `/process-data`

- **Method**: POST
- **Description**: Processes data using a machine learning model and returns optimized parameters.
- **Request Body**: JSON

## Example Requests and Responses

### Example Request to `/process-data`:

```json
{
    "parameters": [
        {"key": "param1", "name": "Parameter 1", "valueType": 0, "value": 10.0, "minValue": 1.0, "maxValue": 20.0, "options": [], "restrictAutoTuning": false, "displayOrder": 0},
        {"key": "param2", "name": "Parameter 2", "valueType": 1, "value": 5, "minValue": 0, "maxValue": 10, "options": [], "restrictAutoTuning": true, "displayOrder": 1}
    ],
    "dataBlobs": [
        {"key": "exampleKey", "data": {"timestamp": "2024-07-24T12:34:56Z", "price": 123.45, "volume": 1000}}
    ]
}

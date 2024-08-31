def mock_ml_model(parameters, data_blobs):
    optimized_parameters = []
    for param in parameters:
        if param["key"] == "param1":
            param["value"] = 15.0  # Mock optimization
        elif param["key"] == "param2":
            param["value"] = 7  # Mock optimization
        optimized_parameters.append({"key": param["key"], "value": param["value"]})
    return optimized_parameters

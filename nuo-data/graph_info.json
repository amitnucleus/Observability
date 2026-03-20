{
    "experiment_id": "697c831b49b6575f3e43a5e8",
    "nodes": [
        {
            "id": "697c85fa49b6575f3e43a69a",
            "type": "textUpdater",
            "transformation_type": "Source",
            "transformation_name": "Source_2",
            "status": "valid",
            "connection_type": "postgres",
            "transformation_category": "data_preprocessing",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "Source",
                "status": "valid",
                "transformation_name": "Source_2",
                "node_count": 2,
                "transformation_category": "data_preprocessing",
                "description": "",
                "mlflow_tracking_properties": [],
                "transformation_properties": [
                    {
                        "property_name": "connection_category",
                        "property_value": "database"
                    },
                    {
                        "property_name": "connection_type",
                        "property_value": "postgres"
                    },
                    {
                        "property_name": "connection_id",
                        "property_value": "6920659c1f213c5a3133553d"
                    },
                    {
                        "property_name": "dataset_id",
                        "property_value": "697c851b6656017bc6737978"
                    },
                    {
                        "property_name": "source_table_id",
                        "property_value": "697c851b6656017bc6737978"
                    },
                    {
                        "property_name": "dataset_name",
                        "property_value": "medicine_data"
                    },
                    {
                        "property_name": "source_table",
                        "property_value": "medicine_data"
                    },
                    {
                        "property_name": "display_rows",
                        "property_value": "10000"
                    },
                    {
                        "property_name": "schema",
                        "property_value": "ingestion_test"
                    }
                ],
                "node_id": "697c85fa49b6575f3e43a69a"
            }
        },
        {
            "id": "697ca31646f1f3fa8cc533f3",
            "type": "textUpdater",
            "transformation_type": "Missing Values",
            "transformation_name": "Missing_Values_3",
            "status": "valid",
            "connection_type": null,
            "transformation_category": "data_preprocessing",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "Missing Values",
                "status": "valid",
                "transformation_name": "Missing_Values_3",
                "node_count": 3,
                "transformation_category": "data_preprocessing",
                "description": "",
                "mlflow_tracking_properties": [],
                "transformation_properties": [
                    {
                        "property_name": "remove_rows",
                        "property_value": "'short_composition2'"
                    }
                ],
                "node_id": "697ca31646f1f3fa8cc533f3"
            }
        },
        {
            "id": "697ca38646f1f3fa8cc5340e",
            "type": "textUpdater",
            "transformation_type": "Duplicates Removal",
            "transformation_name": "Duplicates_Removal_4",
            "status": "valid",
            "connection_type": null,
            "transformation_category": "data_preprocessing",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "Duplicates Removal",
                "status": "valid",
                "transformation_name": "Duplicates_Removal_4",
                "node_count": 4,
                "transformation_category": "data_preprocessing",
                "description": "",
                "mlflow_tracking_properties": [],
                "transformation_properties": [],
                "node_id": "697ca38646f1f3fa8cc5340e"
            }
        },
        {
            "id": "697ca56746f1f3fa8cc53470",
            "type": "textUpdater",
            "transformation_type": "Encoding",
            "transformation_name": "Encoding_6",
            "status": "valid",
            "connection_type": null,
            "transformation_category": "data_preprocessing",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "Encoding",
                "status": "valid",
                "transformation_name": "Encoding_6",
                "node_count": 6,
                "transformation_category": "data_preprocessing",
                "description": "",
                "mlflow_tracking_properties": [],
                "transformation_properties": [
                    {
                        "property_name": "encoding_type",
                        "property_value": "label_encoding"
                    },
                    {
                        "property_name": "columns",
                        "property_value": "'name', 'manufacturer_name', 'type', 'pack_size_label', 'short_composition1', 'short_composition2'"
                    }
                ],
                "node_id": "697ca56746f1f3fa8cc53470"
            }
        },
        {
            "id": "697ca5af46f1f3fa8cc53489",
            "type": "textUpdater",
            "transformation_type": "Scaling",
            "transformation_name": "Scaling_7",
            "status": "valid",
            "connection_type": null,
            "transformation_category": "data_preprocessing",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "Scaling",
                "status": "valid",
                "transformation_name": "Scaling_7",
                "node_count": 7,
                "transformation_category": "data_preprocessing",
                "description": "",
                "mlflow_tracking_properties": [],
                "transformation_properties": [
                    {
                        "property_name": "scaling_type",
                        "property_value": "standard_scaling"
                    },
                    {
                        "property_name": "columns",
                        "property_value": "'name', 'manufacturer_name', 'short_composition2', 'short_composition1', 'pack_size_label', 'type'"
                    }
                ],
                "node_id": "697ca5af46f1f3fa8cc53489"
            }
        },
        {
            "id": "697ca77b46f1f3fa8cc53520",
            "type": "textUpdater",
            "transformation_type": "KNN Regression",
            "transformation_name": "KNN_Regression_10",
            "status": "valid",
            "connection_type": null,
            "transformation_category": "ml_algorithm",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "KNN Regression",
                "status": "valid",
                "transformation_name": "KNN_Regression_10",
                "node_count": 10,
                "transformation_category": "ml_algorithm",
                "description": "",
                "mlflow_tracking_properties": [
                    {
                        "property_name": "input_log_parameters",
                        "property_value": "[\"train_percent\",\"test_percent\",\"validation_percent\",\"independent_variables\",\"dependent_variable\",\"neighbors\",\"metric\",\"algorithm\",\"n_jobs\",\"weight\"]"
                    },
                    {
                        "property_name": "output_metric_parameters",
                        "property_value": "[\"Mean_squared_error\",\"Root_mean_squared_error\",\"Mean_absolute_error\",\"Median_absolute_error\",\"R2_Score\",\"Adjusted_R2\",\"build_time\"]"
                    },
                    {
                        "property_name": "artifact_parameters",
                        "property_value": "[\"training_data\",\"testing_data\"]"
                    }
                ],
                "transformation_properties": [
                    {
                        "property_name": "weights",
                        "property_value": "uniform"
                    },
                    {
                        "property_name": "metric",
                        "property_value": "euclidean"
                    },
                    {
                        "property_name": "n_neighbors",
                        "property_value": "10"
                    },
                    {
                        "property_name": "algorithm",
                        "property_value": "auto"
                    },
                    {
                        "property_name": "n_jobs",
                        "property_value": "2"
                    },
                    {
                        "property_name": "randomization_method",
                        "property_value": "shuffle"
                    },
                    {
                        "property_name": "is_hyper_parameter_tuning_enable",
                        "property_value": "False"
                    },
                    {
                        "property_name": "is_cross_validation_enable",
                        "property_value": "True"
                    },
                    {
                        "property_name": "cross_validation_n_splits",
                        "property_value": "5"
                    },
                    {
                        "property_name": "cross_validation_type",
                        "property_value": "kfold"
                    }
                ],
                "node_id": "697ca77b46f1f3fa8cc53520"
            }
        },
        {
            "id": "697ca8a746f1f3fa8cc53540",
            "type": "textUpdater",
            "transformation_type": "Decision Tree Regression",
            "transformation_name": "Decision_Tree_Regression_11",
            "status": "valid",
            "connection_type": null,
            "transformation_category": "ml_algorithm",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "Decision Tree Regression",
                "status": "valid",
                "transformation_name": "Decision_Tree_Regression_11",
                "node_count": 11,
                "transformation_category": "ml_algorithm",
                "description": "",
                "mlflow_tracking_properties": [
                    {
                        "property_name": "input_log_parameters",
                        "property_value": "[\"train_percent\",\"test_percent\",\"validation_percent\",\"independent_variables\",\"dependent_variable\",\"criterion\",\"max_depth\",\"min_samples_split\",\"max_leaf_nodes\",\"min_weight_fraction_leaf\",\"min_impurity_decrease\",\"ccp_alpha\",\"max_features\",\"min_samples_leaves\",\"splitter\"]"
                    },
                    {
                        "property_name": "output_metric_parameters",
                        "property_value": "[\"Mean_squared_error\",\"Root_mean_squared_error\",\"Mean_absolute_error\",\"Median_absolute_error\",\"R2_Score\",\"Adjusted_R2\",\"build_time\"]"
                    },
                    {
                        "property_name": "artifact_parameters",
                        "property_value": "[\"training_data\",\"testing_data\"]"
                    }
                ],
                "transformation_properties": [
                    {
                        "property_name": "criterion",
                        "property_value": "squared_error"
                    },
                    {
                        "property_name": "max_depth",
                        "property_value": "20"
                    },
                    {
                        "property_name": "min_samples_split",
                        "property_value": "16"
                    },
                    {
                        "property_name": "min_samples_leaf",
                        "property_value": "20"
                    },
                    {
                        "property_name": "max_leaf_nodes",
                        "property_value": "25"
                    },
                    {
                        "property_name": "splitter",
                        "property_value": "best"
                    },
                    {
                        "property_name": "min_weight_fraction_leaf",
                        "property_value": "0.3"
                    },
                    {
                        "property_name": "max_features",
                        "property_value": "log2"
                    },
                    {
                        "property_name": "min_impurity_decrease",
                        "property_value": "7"
                    },
                    {
                        "property_name": "ccp_alpha",
                        "property_value": "8"
                    },
                    {
                        "property_name": "randomization_method",
                        "property_value": "shuffle"
                    },
                    {
                        "property_name": "is_hyper_parameter_tuning_enable",
                        "property_value": "False"
                    },
                    {
                        "property_name": "is_cross_validation_enable",
                        "property_value": "False"
                    }
                ],
                "node_id": "697ca8a746f1f3fa8cc53540"
            }
        },
        {
            "id": "697ca91446f1f3fa8cc53564",
            "type": "textUpdater",
            "transformation_type": "Bagging Regression",
            "transformation_name": "Bagging_Regression_12",
            "status": "valid",
            "connection_type": null,
            "transformation_category": "ml_algorithm",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "Bagging Regression",
                "status": "valid",
                "transformation_name": "Bagging_Regression_12",
                "node_count": 12,
                "transformation_category": "ml_algorithm",
                "description": "",
                "mlflow_tracking_properties": [
                    {
                        "property_name": "input_log_parameters",
                        "property_value": "[\"train_percent\",\"test_percent\",\"validation_percent\",\"independent_variables\",\"dependent_variable\",\"estimator\",\"no_of_estimators\",\"max_samples\",\"max_features\",\"bootstrap\",\"bootstrap_features\",\"oob_score\",\"warm_start\",\"n_jobs\",\"verbose\"]"
                    },
                    {
                        "property_name": "output_metric_parameters",
                        "property_value": "[\"Mean_squared_error\",\"Root_mean_squared_error\",\"Mean_absolute_error\",\"Median_absolute_error\",\"R2_Score\",\"Adjusted_R2\",\"build_time\"]"
                    },
                    {
                        "property_name": "artifact_parameters",
                        "property_value": "[\"training_data\",\"testing_data\"]"
                    }
                ],
                "transformation_properties": [
                    {
                        "property_name": "estimator",
                        "property_value": "KNNRegressor"
                    },
                    {
                        "property_name": "n_estimators",
                        "property_value": "20"
                    },
                    {
                        "property_name": "max_samples",
                        "property_value": "15"
                    },
                    {
                        "property_name": "max_features",
                        "property_value": "7"
                    },
                    {
                        "property_name": "bootstrap",
                        "property_value": "True"
                    },
                    {
                        "property_name": "bootstrap_features",
                        "property_value": "False"
                    },
                    {
                        "property_name": "oob_score",
                        "property_value": "False"
                    },
                    {
                        "property_name": "warm_start",
                        "property_value": "True"
                    },
                    {
                        "property_name": "n_jobs",
                        "property_value": "2"
                    },
                    {
                        "property_name": "verbose",
                        "property_value": "True"
                    },
                    {
                        "property_name": "randomization_method",
                        "property_value": "shuffle"
                    },
                    {
                        "property_name": "is_hyper_parameter_tuning_enable",
                        "property_value": "False"
                    },
                    {
                        "property_name": "is_cross_validation_enable",
                        "property_value": "True"
                    },
                    {
                        "property_name": "cross_validation_n_splits",
                        "property_value": "5"
                    },
                    {
                        "property_name": "cross_validation_type",
                        "property_value": "kfold"
                    }
                ],
                "node_id": "697ca91446f1f3fa8cc53564"
            }
        },
        {
            "id": "697ca9e146f1f3fa8cc53597",
            "type": "textUpdater",
            "transformation_type": "Boosting Regression",
            "transformation_name": "Boosting_Regression_13",
            "status": "valid",
            "connection_type": null,
            "transformation_category": "ml_algorithm",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "Boosting Regression",
                "status": "valid",
                "transformation_name": "Boosting_Regression_13",
                "node_count": 13,
                "transformation_category": "ml_algorithm",
                "description": "",
                "mlflow_tracking_properties": [
                    {
                        "property_name": "input_log_parameters",
                        "property_value": "[\"train_percent\",\"test_percent\",\"validation_percent\",\"independent_variables\",\"dependent_variable\",\"estimator\",\"n_estimators\",\"learning_rate\",\"loss\"]"
                    },
                    {
                        "property_name": "output_metric_parameters",
                        "property_value": "[\"Mean_squared_error\",\"Root_mean_squared_error\",\"Mean_absolute_error\",\"Median_absolute_error\",\"R2_Score\",\"Adjusted_R2\",\"build_time\"]"
                    },
                    {
                        "property_name": "artifact_parameters",
                        "property_value": "[\"training_data\",\"testing_data\"]"
                    }
                ],
                "transformation_properties": [
                    {
                        "property_name": "base_estimator",
                        "property_value": "AdaboostRegressor"
                    },
                    {
                        "property_name": "estimator",
                        "property_value": "DecisionTreeRegressor"
                    },
                    {
                        "property_name": "n_estimators",
                        "property_value": "10"
                    },
                    {
                        "property_name": "learning_rate",
                        "property_value": "0.6"
                    },
                    {
                        "property_name": "loss",
                        "property_value": "square"
                    },
                    {
                        "property_name": "randomization_method",
                        "property_value": "shuffle"
                    },
                    {
                        "property_name": "is_hyper_parameter_tuning_enable",
                        "property_value": "False"
                    },
                    {
                        "property_name": "is_cross_validation_enable",
                        "property_value": "False"
                    }
                ],
                "node_id": "697ca9e146f1f3fa8cc53597"
            }
        },
        {
            "id": "697caa8f46f1f3fa8cc535c0",
            "type": "textUpdater",
            "transformation_type": "Random Forest Regression",
            "transformation_name": "Random_Forest_Regression_14",
            "status": "valid",
            "connection_type": null,
            "transformation_category": "ml_algorithm",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "Random Forest Regression",
                "status": "valid",
                "transformation_name": "Random_Forest_Regression_14",
                "node_count": 14,
                "transformation_category": "ml_algorithm",
                "description": "",
                "mlflow_tracking_properties": [
                    {
                        "property_name": "input_log_parameters",
                        "property_value": "[\"train_percent\",\"test_percent\",\"validation_percent\",\"independent_variables\",\"dependent_variable\",\"criterion\",\"max_depth\",\"min_samples_split\",\"max_leaf_nodes\",\"min_weight_fraction_leaf\",\"min_impurity_decrease\",\"ccp_alpha\",\"max_features\",\"min_samples_leaves\",\"splitter\",\"estimators\"]"
                    },
                    {
                        "property_name": "output_metric_parameters",
                        "property_value": "[\"Mean_squared_error\",\"Root_mean_squared_error\",\"Mean_absolute_error\",\"Median_absolute_error\",\"R2_Score\",\"Adjusted_R2\",\"build_time\"]"
                    },
                    {
                        "property_name": "artifact_parameters",
                        "property_value": "[\"training_data\",\"testing_data\"]"
                    }
                ],
                "transformation_properties": [
                    {
                        "property_name": "criterion",
                        "property_value": "squared_error"
                    },
                    {
                        "property_name": "max_depth",
                        "property_value": "20"
                    },
                    {
                        "property_name": "min_samples_split",
                        "property_value": "10"
                    },
                    {
                        "property_name": "min_samples_leaf",
                        "property_value": "15"
                    },
                    {
                        "property_name": "max_leaf_nodes",
                        "property_value": "25"
                    },
                    {
                        "property_name": "n_estimators",
                        "property_value": "10"
                    },
                    {
                        "property_name": "min_weight_fraction_leaf",
                        "property_value": "0.3"
                    },
                    {
                        "property_name": "max_features",
                        "property_value": "log2"
                    },
                    {
                        "property_name": "min_impurity_decrease",
                        "property_value": "3"
                    },
                    {
                        "property_name": "ccp_alpha",
                        "property_value": "5"
                    },
                    {
                        "property_name": "randomization_method",
                        "property_value": "shuffle"
                    },
                    {
                        "property_name": "is_hyper_parameter_tuning_enable",
                        "property_value": "False"
                    },
                    {
                        "property_name": "is_cross_validation_enable",
                        "property_value": "False"
                    }
                ],
                "node_id": "697caa8f46f1f3fa8cc535c0"
            }
        },
        {
            "id": "697cab8b46f1f3fa8cc535eb",
            "type": "textUpdater",
            "transformation_type": "Linear Regression",
            "transformation_name": "Linear_Regression_15",
            "status": "valid",
            "connection_type": null,
            "transformation_category": "ml_algorithm",
            "node_details": {
                "experiment_id": "697c831b49b6575f3e43a5e8",
                "type": "textUpdater",
                "transformation_type": "Linear Regression",
                "status": "valid",
                "transformation_name": "Linear_Regression_15",
                "node_count": 15,
                "transformation_category": "ml_algorithm",
                "description": "",
                "mlflow_tracking_properties": [
                    {
                        "property_name": "input_log_parameters",
                        "property_value": "[\"train_percent\",\"test_percent\",\"validation_percent\",\"independent_variables\",\"dependent_variable\",\"fit_intercept\",\"copy_X\",\"n_jobs\",\"positive\"]"
                    },
                    {
                        "property_name": "output_metric_parameters",
                        "property_value": "[\"Mean_squared_error\",\"Root_mean_squared_error\",\"Mean_absolute_error\",\"Median_absolute_error\",\"Median_absoulte_error\",\"R2_Score\",\"Adjusted_R2\",\"build_time\"]"
                    },
                    {
                        "property_name": "artifact_parameters",
                        "property_value": "[\"training_data\",\"testing_data\"]"
                    }
                ],
                "transformation_properties": [
                    {
                        "property_name": "fit_intercept",
                        "property_value": "True,False"
                    },
                    {
                        "property_name": "copy_X",
                        "property_value": "True"
                    },
                    {
                        "property_name": "n_jobs",
                        "property_value": "1"
                    },
                    {
                        "property_name": "positive",
                        "property_value": "True,False"
                    },
                    {
                        "property_name": "randomization_method",
                        "property_value": "shuffle"
                    },
                    {
                        "property_name": "is_hyper_parameter_tuning_enable",
                        "property_value": "True"
                    },
                    {
                        "property_name": "tuning_type",
                        "property_value": "grid_search"
                    },
                    {
                        "property_name": "hyper_parameter_n_splits",
                        "property_value": "3"
                    }
                ],
                "node_id": "697cab8b46f1f3fa8cc535eb"
            }
        }
    ],
    "edges": [
        {
            "id": "697ca32746f1f3fa8cc533fa",
            "source_node_id": "697c85fa49b6575f3e43a69a",
            "target_node_id": "697ca31646f1f3fa8cc533f3",
            "transformation_type": "edge",
            "ui_details": {
                "sourceHandle": null,
                "targetHandle": null
            }
        },
        {
            "id": "697ca39846f1f3fa8cc53417",
            "source_node_id": "697ca31646f1f3fa8cc533f3",
            "target_node_id": "697ca38646f1f3fa8cc5340e",
            "transformation_type": "edge",
            "ui_details": {
                "sourceHandle": null,
                "targetHandle": null
            }
        },
        {
            "id": "697ca57a46f1f3fa8cc53476",
            "source_node_id": "697ca38646f1f3fa8cc5340e",
            "target_node_id": "697ca56746f1f3fa8cc53470",
            "transformation_type": "edge",
            "ui_details": {
                "sourceHandle": null,
                "targetHandle": null
            }
        },
        {
            "id": "697ca5c046f1f3fa8cc53499",
            "source_node_id": "697ca56746f1f3fa8cc53470",
            "target_node_id": "697ca5af46f1f3fa8cc53489",
            "transformation_type": "edge",
            "ui_details": {
                "sourceHandle": null,
                "targetHandle": null
            }
        },
        {
            "id": "697ca86d46f1f3fa8cc5352e",
            "source_node_id": "697ca5af46f1f3fa8cc53489",
            "target_node_id": "697ca77b46f1f3fa8cc53520",
            "transformation_type": "edge",
            "ui_details": {
                "sourceHandle": null,
                "targetHandle": null
            }
        },
        {
            "id": "697ca8bd46f1f3fa8cc53550",
            "source_node_id": "697ca5af46f1f3fa8cc53489",
            "target_node_id": "697ca8a746f1f3fa8cc53540",
            "transformation_type": "edge",
            "ui_details": {
                "sourceHandle": null,
                "targetHandle": null
            }
        },
        {
            "id": "697ca92846f1f3fa8cc53572",
            "source_node_id": "697ca5af46f1f3fa8cc53489",
            "target_node_id": "697ca91446f1f3fa8cc53564",
            "transformation_type": "edge",
            "ui_details": {
                "sourceHandle": null,
                "targetHandle": null
            }
        },
        {
            "id": "697caa0046f1f3fa8cc535a7",
            "source_node_id": "697ca5af46f1f3fa8cc53489",
            "target_node_id": "697ca9e146f1f3fa8cc53597",
            "transformation_type": "edge",
            "ui_details": {
                "sourceHandle": null,
                "targetHandle": null
            }
        },
        {
            "id": "697caaa446f1f3fa8cc535d0",
            "source_node_id": "697ca5af46f1f3fa8cc53489",
            "target_node_id": "697caa8f46f1f3fa8cc535c0",
            "transformation_type": "edge",
            "ui_details": {
                "sourceHandle": null,
                "targetHandle": null
            }
        },
        {
            "id": "697caba146f1f3fa8cc535fa",
            "source_node_id": "697ca5af46f1f3fa8cc53489",
            "target_node_id": "697cab8b46f1f3fa8cc535eb",
            "transformation_type": "edge",
            "ui_details": {
                "sourceHandle": null,
                "targetHandle": null
            }
        }
    ]
}
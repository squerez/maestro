import pytest
from unittest import mock

from maestro.core import Task, ConfigReader


@pytest.fixture
def reader():
    return ConfigReader

def test_from_yaml_file_on_valid_file(reader):
    tasks = reader.from_yaml('tests/core/config/yaml/valid.yaml')
    assert len(tasks) > 0

def test_from_yaml_invalid_file_missing_name(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_yaml("tests/core/config/yaml/missing_name.yaml")
    error_msg = "Invalid task: missing 'name' field"
    assert error_msg in str(exc_info.value)

def test_from_yaml_invalid_file_duplicate_name(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_yaml("tests/core/config/yaml/duplicate_name.yaml")
    error_msg = "Duplicate task name"
    assert error_msg in str(exc_info.value)

def test_from_yaml_invalid_file_invalid_dependencies(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_yaml("tests/core/config/yaml/invalid_dependencies.yaml")
    error_msg = "Invalid dependencies for task"
    assert error_msg in str(exc_info.value)

def test_from_yaml_invalid_file_undefined_dependency(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_yaml("tests/core/config/yaml/undefined_dependencies.yaml")
    error_msg = "Invalid dependencies: some tasks are referenced but not defined"
    assert error_msg in str(exc_info.value)

def test_from_yaml_invalid_file_duplicated_dependency(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_yaml("tests/core/config/yaml/duplicated_dependencies.yaml")
    error_msg = "Duplicate dependencies found for task"
    assert error_msg in str(exc_info.value)

def test_from_yaml_invalid_file_circular_references(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_yaml("tests/core/config/yaml/circular_reference.yaml")
    error_msg = "Circular references detected"
    assert error_msg in str(exc_info.value)

# -----------------------------
# -----------------------------
# -----------------------------

def test_from_json_file_on_valid_file(reader):
    tasks = reader.from_json('tests/core/config/json/valid.json')
    assert len(tasks) > 0

def test_from_json_invalid_file_missing_name(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_json("tests/core/config/json/missing_name.json")
    error_msg = "Invalid task: missing 'name' field"
    assert error_msg in str(exc_info.value)

def test_from_json_invalid_file_duplicate_name(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_json("tests/core/config/json/duplicate_name.json")
    error_msg = "Duplicate task name"
    assert error_msg in str(exc_info.value)

def test_from_json_invalid_file_invalid_dependencies(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_json("tests/core/config/json/invalid_dependencies.json")
    error_msg = "Invalid dependencies for task"
    assert error_msg in str(exc_info.value)

def test_from_json_invalid_file_undefined_dependency(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_json("tests/core/config/json/undefined_dependencies.json")
    error_msg = "Invalid dependencies: some tasks are referenced but not defined"
    assert error_msg in str(exc_info.value)

def test_from_json_invalid_file_duplicated_dependency(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_json("tests/core/config/json/duplicated_dependencies.json")
    error_msg = "Duplicate dependencies found for task"
    assert error_msg in str(exc_info.value)

def test_from_json_invalid_file_circular_references(reader):
    with pytest.raises(ValueError) as exc_info:
        reader.from_yaml("tests/core/config/json/circular_reference.json")
    error_msg = "Circular references detected"
    assert error_msg in str(exc_info.value)

# -----------------------------
# -----------------------------
# -----------------------------

def test_parse_tasks(reader):

    data = [
        {"name": "Task1", "dependencies": ["Task2"]},
        {"name": "Task2", "dependencies": ["Task3"]},  
        {"name": "Task3", "dependencies": []},
    ]    
    tasks = reader._parse_tasks(data)
    assert len(tasks) == 3

    task_names = [task.name for task in tasks]
    assert "Task1" in task_names
    assert "Task2" in task_names
    assert "Task3" in task_names

    assert tasks[0].dependencies == [tasks[1].name]
    assert tasks[1].dependencies == [tasks[2].name]
    assert tasks[2].dependencies == []

def test_parse_tasks_error(reader):
    data = [{"dependencies": ["Task2"]}]

    with mock.patch.object(ConfigReader, '_parse_tasks') as mock_parse_tasks:
        mock_parse_tasks.side_effect = Exception("Error parsing tasks from configuration")

        with pytest.raises(Exception) as exc_info:
            reader._parse_tasks(data)
        assert str(exc_info.value) == "Error parsing tasks from configuration"

    mock_parse_tasks.assert_called_once_with(data)

# -----------------------------
# -----------------------------
# -----------------------------

def test_validate_tasks(reader):
    data = [
        {"name": "Task1", "dependencies": ["Task2"]},
        {"name": "Task2", "dependencies": ["Task3"]},
        {"name": "Task3", "dependencies": []},
    ]
    reader._validate_tasks(data)

def test_validate_tasks_duplicate_task_name(reader):
    data = [
        {"name": "Task1", "dependencies": []},
        {"name": "Task1", "dependencies": []},
    ]

    with pytest.raises(ValueError) as exc_info:
        reader._validate_tasks(data)
    error_msg = "Duplicate task name"
    assert error_msg in str(exc_info.value)

def test_validate_tasks_invalid_dependencies(reader):
    data = [
        {"name": "Task1", "dependencies": ["Task2"]},
        {"name": "Task2", "dependencies": "Task3"},
        {"name": "Task3", "dependencies": []},
    ]

    with pytest.raises(ValueError) as exc_info:
        reader._validate_tasks(data)
    error_msg = "Invalid dependencies for task"
    assert error_msg in str(exc_info.value)

def test_validate_tasks_invalid_task_name(reader):
    data = [
        {"name": "", "dependencies": []},
        {"name": "Task2", "dependencies": []},
    ]

    with pytest.raises(ValueError) as exc_info:
        reader._validate_tasks(data)
    error_msg = "Invalid task: missing 'name' field"
    assert error_msg in str(exc_info.value)

def test_validate_tasks_undefined_dependencies(reader):
    data = [
        {"name": "Task1", "dependencies": ["Task2"]},
    ]

    with pytest.raises(ValueError) as exc_info:
        reader._validate_tasks(data)
    error_msg = "Invalid dependencies: some tasks are referenced but not defined"
    assert error_msg in str(exc_info.value)


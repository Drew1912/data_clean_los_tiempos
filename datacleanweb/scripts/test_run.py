from core_processor import DataProcessor
import json

if __name__ == "__main__":
    print("Testing core logic...")
    processor = DataProcessor()
    result = processor.process_files("ventas_test.csv", "contabilidad_test.csv")
    print(json.dumps(result, indent=4))

import csv
import json
import sys


def csv_to_jsonl(csv_file_path, jsonl_file_path):
    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        with open(jsonl_file_path, 'w') as jsonl_file:
            for row in csv_reader:
                messages = []
                messages.append({"role": "system", "content": "You are an assistant and you are tasked with answer questions about a company called Odd-e. For each input question, provide an answer. The answer should be accurate and truthful. Do not make up facts or answers"})
                messages.append({"role": "user", "content": row["instruction"]})
                messages.append({"role": "assistant", "content": row["response"]})
                jsonl_file.write(json.dumps({"messages": messages}) + '\n')

# Example usage
csv_file_path = sys.argv[1]
jsonl_file_path = sys.argv[2]
csv_to_jsonl(csv_file_path, jsonl_file_path)
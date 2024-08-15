from langsmith import Client
import json

formatted_data = []

ls_client = Client()
label_data = ls_client.list_examples(dataset_name="XCommentClassification")

for entry in label_data:
    post = entry.inputs["text"]
    label = entry.outputs["label"]
    formatted_entry = {"text": post, "label": label}
    formatted_data.append(formatted_entry)

print(f"Number of training examples: {len(formatted_data)}")

# Write formatted data to a JSONL file
with open("training_data.jsonl", "w") as file:
    for data_entry in formatted_data:
        # Convert dictionary to JSON string and write to file
        json_string = json.dumps(data_entry)
        file.write(json_string + "\n")
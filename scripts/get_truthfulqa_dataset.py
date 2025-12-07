import pandas as pd

# 1. Read the dataset from Hugging Face
# (Note: This uses the 'huggingface_hub' library to handle the 'hf://' protocol)
df = pd.read_csv("hf://datasets/domenicrosati/TruthfulQA/train.csv")

print(df.head())  # Print the first few

# 2. Save the dataframe to a CSV file on your PC
# 'index=False' prevents pandas from adding a separate column for row numbers
df.to_csv("truthful_qa_dataset.csv", index=False)

print("Dataset successfully saved as 'truthful_qa_dataset.csv'")

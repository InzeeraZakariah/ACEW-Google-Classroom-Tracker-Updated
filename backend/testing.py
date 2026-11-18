from store_data import load_json, save_json

# Test reading
subjects = load_json("subjects.json")
print("Read successful:", type(subjects).__name__)

# Test writing the same data back
save_json("subjects.json", subjects)
print("Write successful")

# Verify the saved data
verified_subjects = load_json("subjects.json")
print("Verification successful:", verified_subjects == subjects)
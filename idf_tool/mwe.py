def insert_at_index(d, key, value, index):
    """
    Insert a key-value pair at a specific index in a dictionary.
    
    :param d: The original dictionary
    :param key: The key to insert
    :param value: The value to insert
    :param index: The index at which to insert the key-value pair
    :return: A new dictionary with the key-value pair inserted at the specified index
    """
    new_dict = {}
    
    if index is None:
        index = 999

    for i, (k, v) in enumerate(d.items()):
        if i == index:
            new_dict[key] = value
        new_dict[k] = v
    
    if index >= len(d):
        new_dict[key] = value
    
    return new_dict

original_dict = {'a': 1, 'b': 2, 'c': 3}
new_key = 'd'
new_value = 4

# Append the new key-value pair to the end of the dictionary
new_dict = insert_at_index(original_dict, new_key, new_value, None)
print(new_dict)
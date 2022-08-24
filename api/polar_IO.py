

# -------- UTILITY FUNCTIONS -------- #
def flatten_list(l):
    return [item for sublist in l for item in sublist]

# from https://stackoverflow.com/questions/1060279/iterating-through-a-range-of-dates-in-python
def daterange(start_date, end_date):
    add_date = timedelta(days=1)
    for n in range(int(((end_date + add_date) - start_date).days)):
        yield start_date + timedelta(n)
        
def get_key(val, my_dict):
    for key, value in my_dict.items():
         if val == value:
             return key
    return "key doesn't exist"
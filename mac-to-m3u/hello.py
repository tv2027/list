import csv

print ("Hello, World!")

with open('data.csv', mode='r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        print(row)  # Access by header name




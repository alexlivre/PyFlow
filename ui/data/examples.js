// Example snippets shown in the editor "Examples" dropdown.
// Each example: { title, description, code }

export const examples = [
  {
    title: 'Hello World',
    description: 'The classic first program: print a greeting to the console.',
    code: `# The classic first program
print("Hello, World!")
print("Welcome to PyFlow")
`,
  },
  {
    title: 'Loops',
    description: 'Iterate with for and while loops.',
    code: `# For and while loops

# for: iterate over a fixed sequence
for i in range(1, 6):
    print(f"for: {i}")

# while: repeat while a condition holds
count = 5
while count > 0:
    print(f"while: {count}")
    count -= 1
`,
  },
  {
    title: 'Lists',
    description: 'Create, modify and slice a list of items.',
    code: `# Working with lists
fruits = ["apple", "banana", "cherry"]

fruits.append("grape")
fruits.insert(1, "blueberry")

print("All fruits:", fruits)
print("First:", fruits[0])
print("Last:", fruits[-1])
print("Slice:", fruits[1:3])

for fruit in fruits:
    print(f"- {fruit}")
`,
  },
  {
    title: 'Dictionaries',
    description: 'Store key-value pairs and iterate over them.',
    code: `# Working with dictionaries
person = {
    "name": "Alice",
    "age": 25,
    "city": "Sao Paulo",
}

print(person["name"])
person["age"] = 26
person["job"] = "Developer"

for key, value in person.items():
    print(f"{key}: {value}")

print("City:", person.get("city", "unknown"))
print("Phone:", person.get("phone", "not set"))
`,
  },
  {
    title: 'Functions',
    description: 'Define functions with default arguments and docstrings.',
    code: `# Defining and calling functions
def add(a, b=10):
    """Return the sum of two numbers."""
    return a + b

def describe(name, age=None):
    if age is None:
        return f"{name} (age unknown)"
    return f"{name}, {age} years old"

print(add(5))
print(add(5, 20))
print(describe("Bob"))
print(describe("Alice", 30))
`,
  },
  {
    title: 'Classes & OOP',
    description: 'Model a bank account with methods and attributes.',
    code: `# A simple bank account class
class Account:
    def __init__(self, owner, balance=0):
        self.owner = owner
        self.balance = balance

    def deposit(self, amount):
        self.balance += amount
        print(f"{self.owner} deposited {amount}")

    def withdraw(self, amount):
        if amount > self.balance:
            print("Insufficient funds")
            return
        self.balance -= amount
        print(f"{self.owner} withdrew {amount}")

acc = Account("Alice", 100)
acc.deposit(50)
acc.withdraw(30)
print(f"Balance: {acc.balance}")
`,
  },
  {
    title: 'ASCII Art Shapes',
    description: 'Draw shapes with plain text — works headless, no graphics window needed.',
    code: `# Text-based shape drawing (no GUI window required)
def draw_square(size):
    for _ in range(size):
        print("* " * size)

def draw_triangle(size):
    for row in range(1, size + 1):
        print("* " * row)

print("Square:")
draw_square(5)

print("Triangle:")
draw_triangle(5)
`,
  },
  {
    title: 'Matplotlib Plot',
    description: 'Plot a sine wave with matplotlib (no numpy needed). The figure is returned as an inline image in the output.',
    code: `# Plot a sine wave with matplotlib
# The figure is rendered inline in the output panel
import math
import matplotlib.pyplot as plt

x = [i / 50 for i in range(100)]  # 0.00 to 1.98
y = [math.sin(v * 2 * math.pi) for v in x]

plt.plot(x, y, label="sin(2πx)", color="crimson")
plt.xlabel("x")
plt.ylabel("sin(x)")
plt.title("Sine Wave")
plt.grid(True)
plt.legend()
plt.show()
`,
  },
  {
    title: 'Deliberate Error',
    description: 'This code fails on purpose to show the diagnostics tab.',
    code: `# This example fails on purpose to show the diagnostics tab
numbers = [10, 20, 30]
index = 5

print(numbers[index])  # IndexError: list index out of range
`,
  },
  {
    title: 'User Input',
    description: 'Ask the user for their name and greet them. Interactive input may not work in the web sandbox.',
    code: `# Ask the user for their name and greet them
# Note: interactive input may not work in the web sandbox
name = input("What is your name? ")
print(f"Hello, {name}!")
`,
  },
  {
    title: 'Recursion',
    description: 'Compute factorials with a recursive function.',
    code: `# Factorial via recursion
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

for i in range(1, 8):
    print(f"{i}! = {factorial(i)}")
`,
  },
  {
    title: 'Comprehensions & f-strings',
    description: 'Build lists with comprehensions and format output with f-strings.',
    code: `# List comprehensions and formatted strings
squares = [n ** 2 for n in range(1, 11)]
even = [n for n in squares if n % 2 == 0]

for n in even:
    print(f"{n:>3} is even")

print(f"Total: {len(even)} even squares")
`,
  },
]

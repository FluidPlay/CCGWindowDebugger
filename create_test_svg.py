import re

with open('GenPowersShortcutBarUS.svg', 'r') as f:
    content = f.read()

# Change x="752" to x="100" in the first occurrence (or all)
# This roughly corresponds to GenPowersShortcutBarParent
new_content = content.replace('x="752"', 'x="100"')

with open('test_update.svg', 'w') as f:
    f.write(new_content)
print("Created test_update.svg")

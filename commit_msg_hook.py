from commit_checker import get_staged_diff
from commit_checker import total_touched_lines
from commit_checker import is_message_true
from commit_checker import ai_evaluation
import sys

#text colors:
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
RESET = "\033[0m"

with open(sys.argv[1],"r") as file:
    staged_message = file.read()

diff_text = get_staged_diff()
lines_touched = total_touched_lines(diff_text)
evaluation = ai_evaluation(staged_message, diff_text)

if is_message_true(staged_message, lines_touched):
    print("Passed the initial observation✅")
else:
    print("Did NOT pass the initial observation❌")

if evaluation is not None:
    print(f"\n{MAGENTA}Commit message accuracy:{RESET} {evaluation['accuracy_score']}\n\n{BLUE}Information about the commit:{RESET} {evaluation['reasoning']}\n\n{YELLOW}Suggested Commit Message:{RESET} {evaluation['suggested_message']}")
    if evaluation['accuracy_score'] < 5:
        sys.exit(1)
elif evaluation is None:
    sys.exit(1)



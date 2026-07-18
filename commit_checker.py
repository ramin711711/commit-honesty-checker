import argparse
import anthropic
import subprocess
import sys
import json
import re
from dotenv import load_dotenv
load_dotenv()

#text colors:
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
RESET = "\033[0m"

SMALL_FIX_KEYWORDS = {
    "typo","typos","minor","small","tiny","quick","trivial","simple","slight","little","micro","minimal","miniscule",
    "minute","cosmetic","tweak","tweaks","tweakup","adjust","adjustment","adjustments","polish","polishing","lint","linting",
    "format","formatting","whitespace","spacing","indent","indentation","comment","comments","docs","doc","documentation",
    "readme","style","styling","consistency","clarify","clarification","improve wording","wording","grammar","spelling", "punctuation"
}

def get_diff(old_commit, new_commit):
    """Return the raw `git diff` text between two commits, using subprocess to call git directly."""
    result = subprocess.run(
        ["git", "diff", old_commit, new_commit],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout

def get_staged_diff():
    result = subprocess.run(
        ["git", "diff", "--staged"],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout

def get_commit_message(commit):
    """Return the commit message text for a single commit (with removed whitespaces) ."""
    commit_msg = subprocess.run(
        ["git", "log", "-1", "--pretty=%B", commit],
        capture_output=True,
        text=True,
        check=True
    )
    return commit_msg.stdout.strip()

def total_touched_lines(text):
    """Count total lines added and removed in a diff, ignoring the '+++'/'---' file header lines."""
    text = text.split("\n")
    total_additions = 0
    total_deletions = 0
    for t in text:
        if t.startswith('+') and not t.startswith('+++'):
            total_additions += 1
        elif t.startswith('-') and not t.startswith('---'):
            total_deletions += 1
    return total_additions + total_deletions

def is_message_true(commit_msg, lines_touched, threshold=20):
    """Check whether a commit message claiming a 'small' change is honest about its size.
    Returns False if the message contains a small-change keyword but the diff exceeds the threshold."""
    commit_msg = commit_msg.lower()
    for keyword in SMALL_FIX_KEYWORDS:
        if re.search(r"\b" + keyword + r"\b", commit_msg):
            if lines_touched > threshold:
                return False

    return True

def ai_evaluation(commit_msg, diff_text):
    """Send the commit message and diff to Claude for a semantic honesty check.
    Returns a dict with an accuracy score (1-10), reasoning, and a suggested commit message."""
    try:
        client = anthropic.Anthropic() 
 
        prompt = f"""You are reviewing a git commit to check if the commit message honestly describes the code changes.
                Commit message: "{commit_msg}" | Diff: {diff_text}
                Respond with ONLY a JSON object, no other text, in this exact format: {{"accuracy_score": <int 1-10>, "reasoning": "<short explanation>", "suggested_message": "<a more accurate commit message>"}} 
                suggested_message should be a single line, git-commit-subject-line style, under ~72 characters
                MAKE SURE THAT YOUR JSON RESPOND is not geting wrapped by ```json or ```"""
        
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        response = message.content[0].text

        if response.startswith("```"):
            response = response.replace("```json", "").replace("```", "")
    
        data = json.loads(response.strip())
        return data
    except anthropic.APIError:
        print(f"{RED}Something went wrong when trying to get a response from AI{RESET}")
        return None
    except json.JSONDecodeError:
        print(f"{RED}Json Decoding was unsuccessfull{RESET}")
        return None
    



if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--old_commit", type=str, help="Provide an old commit")
    parser.add_argument("-n", "--new_commit", type=str, help="Provide a new commit")
    parser.add_argument("-t", "--threshold", type=int, help="Provide a threshold for the honesty checker")
    parser.add_argument("--strict", action="store_true", help="Exit with code 1 if the commit message fails the honesty/AI accuracy check (blocks the commit)")
    args = parser.parse_args()

    diff_text = get_diff(args.old_commit, args.new_commit)
    commit_message = get_commit_message(args.new_commit)
    lines_touched = total_touched_lines(diff_text)
    evaluation = ai_evaluation(commit_message, diff_text)

    if is_message_true(commit_message, lines_touched, args.threshold):
        print("Passed the initial observation: size check -> honest ✅")
    else:
        print("Did NOT pass the initial observation: size check -> dishonest ❌")

    if evaluation is not None:
        print(f"\nAI semantic check:")
        print(f"\n{MAGENTA}Commit message accuracy:{RESET} {evaluation['accuracy_score']}\n\n{BLUE}Information about the commit:{RESET} {evaluation['reasoning']}\n\n{YELLOW}Suggested Commit Message:{RESET} {evaluation['suggested_message']}")
    
    if args.strict:
        if evaluation is None:
            sys.exit(1)
        if evaluation['accuracy_score'] < 5:
            sys.exit(1)
 
            


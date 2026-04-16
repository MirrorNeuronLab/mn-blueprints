#!/usr/bin/env python3
import json
import math
import sys


def classify(number: int) -> dict:
    if number < 2:
        return {
            "candidate": number,
            "is_prime": False,
            "reason": "less_than_two",
            "checked_limit": 1,
        }

    if number == 2:
        return {
            "candidate": number,
            "is_prime": True,
            "checked_limit": 2,
        }

    if number % 2 == 0:
        return {
            "candidate": number,
            "is_prime": False,
            "smallest_divisor": 2,
            "checked_limit": 2,
        }

    limit = int(math.isqrt(number))
    for divisor in range(3, limit + 1, 2):
        if number % divisor == 0:
            return {
                "candidate": number,
                "is_prime": False,
                "smallest_divisor": divisor,
                "checked_limit": divisor,
            }

    return {
        "candidate": number,
        "is_prime": True,
        "checked_limit": limit,
    }


def main() -> None:
    number = int(sys.argv[1])
    print(json.dumps(classify(number)))


if __name__ == "__main__":
    main()

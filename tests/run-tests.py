#!/usr/bin/python3

from subprocess import Popen, PIPE
from os.path import abspath, dirname, join
from sys import argv, stderr

TESTS=[
("example1.txt", 1, 0),
("example2.txt", 2, 1),
("example3.txt", 1, 0),
("example4.txt", 2, 1),
("fib.txt", 1, 0),
("gcd.txt", 1, 0),
("gcd2.txt", 30, 16),
("simple-loop.txt", 1, 0),
("simple-nondet.txt", 3, 1),
("sum.txt", 1, 0)
]

def main(se):
    total, failed = 0, 0
    for program, nop, noe in TESTS:
        total += 1
        cmd = [abspath(se), abspath(join(dirname(argv[0]), program))]
        print('Running: ', " ".join(cmd))
        P = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = P.communicate()
        if out is None:
            print(f"{program}... failed")
            failed += 1
            continue

        nopstr = f"Executed paths: {nop}"
        noestr = f"Error paths: {noe}"

        have_nopstr = False
        have_noestr = False
        for line in (l.strip().decode('utf-8') for l in out.splitlines()):
            if line == nopstr:
                have_nopstr = True
            elif line == noestr:
                have_noestr = True

        if not have_nopstr or not have_noestr:
            print(f"{program}... failed")
            failed += 1
        else:
            print(f"{program}... ok")

    print(f"Result: {failed} of {total} failed")

if __name__ == "__main__":
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <symbolic-executor>", file=stderr)
        exit(1)

    main(argv[1])

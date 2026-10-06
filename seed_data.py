"""
seed_data.py - static plan data and the pure lookup Functions from the VBA module.

VBA origin
----------
  InitPhases / SetPhase        -> PHASES
  WeekFocus                    -> week_focus()
  WeekDsa                      -> week_dsa()
  PhaseOfWeek                  -> phase_of_week()
  IsCheckpointWeek             -> is_checkpoint_week()
  DayPlanText                  -> day_plan_text()
  LoadTaskData (AddTask calls) -> TASKS   (extracted mechanically: 105 rows)
  BuildLogsSheet skill array   -> SKILLS
  BuildLists (PutList calls)   -> exposed via the enums in models.py

Nothing in here touches the database; services.seed_database() consumes it.
"""
from __future__ import annotations

from typing import Final

WEEKS_TOTAL: Final[int] = 18
BLOCKS_PER_WEEK: Final[int] = 17          # Mon-Fri 3 blocks + Sat 1 + Sun 1
DEFAULT_WEEKLY_PLANNED_HOURS: Final[float] = 19.0

# (id, label, week_start, week_end).  id 0 = Setup, 1-6 = Phases 1-6, 7 = Tracks
PHASES: Final[list[tuple[int, str, int, int]]] = [
    (0, "Setup - Before Week 1", 0, 0),
    (1, "P1 - Linux, Bash, Git, Networking", 1, 3),
    (2, "P2 - Python, SQL, DBMS", 4, 6),
    (3, "P3 - REST and FastAPI rebuild", 7, 8),
    (4, "P4 - Docker, Compose, CI/CD", 9, 11),
    (5, "P5 - AWS, Terraform, Kubernetes", 12, 15),
    (6, "P6 - System Design, Revision, Interviews", 16, 18),
    (7, "Tracks - DSA, Jobs, Weekly Review", 1, 18),
]

CHECKPOINT_WEEKS: Final[frozenset[int]] = frozenset({3, 6, 8, 11, 15, 18})

# (type, skill)
SKILLS: Final[list[tuple[str, str]]] = [
    ("Must-have", "Linux commands + permissions"),
    ("Must-have", "Bash scripting"),
    ("Must-have", "Git (branching, conflicts)"),
    ("Must-have", "Networking (DNS, HTTP, subnets)"),
    ("Must-have", "OS concepts"),
    ("Must-have", "Python scripting"),
    ("Must-have", "SQL + DBMS"),
    ("Must-have", "REST + FastAPI"),
    ("Should", "Testing (pytest)"),
    ("Must-have", "Docker + Compose"),
    ("Must-have", "GitHub Actions CI/CD"),
    ("Must-have", "AWS core (IAM, VPC, EC2, S3)"),
    ("Must-have", "Terraform"),
    ("Should", "Kubernetes basics"),
    ("Should", "Prometheus + Grafana"),
    ("Must-have", "DSA (easy)"),
    ("Should", "DSA (medium)"),
    ("Should", "System design basics"),
    ("Must-have", "Explaining my projects aloud"),
    ("Nice-to-have", "React.js"),
]

_WEEK_FOCUS: Final[list[str]] = [
    "Baseline + Linux basics", "Linux services + Bash", "Git + Networking",
    "Python core 1", "Python core 2 + CLI", "SQL + DBMS (start applying)",
    "REST + FastAPI rebuild", "Testing, migrations, auth basics", "Docker deep",
    "Compose + Actions 1 (resume v2)", "Full CI/CD + scanning", "AWS core",
    "Terraform on AWS", "Kubernetes basics", "Capstone on AWS",
    "System design + revision (resume v3)", "Mock interviews", "Polish + apply sprint",
]

_WEEK1_DAYS: Final[list[str]] = [
    "Baseline: rate skills 0-3, run diagnostic P02, Linux filesystem + core commands | DSA: Two Sum",
    "Job reality check: collect 10 JDs, update gap table | users, groups, permissions | DSA: Contains Duplicate",
    "Processes + services: ps/top/kill/systemctl/journalctl/apt, install nginx, read logs | DSA: Valid Anagram",
    "Text tools: pipes, grep, sed, awk, cut, sort, uniq; errors-per-hour one-liner; quiz P11",
    "First Bash script: server-health.sh v1 (disk + memory OK/WARN) | re-do Two Sum from scratch",
    "Build (5h): finish server-health.sh, push to GitHub with README, fix resume placeholders (CGPA, internship dates)",
    "Weekly review (P32), fill the Week 1 tracker row, plan Week 2, rest",
]


def week_focus(week: int) -> str:
    """VBA WeekFocus (1-based week)."""
    return _WEEK_FOCUS[week - 1]


def week_dsa(week: int) -> str:
    """VBA WeekDsa."""
    if week == 1:
        return "Setup + 3 warm-ups"
    if week in (2, 3):
        return "Arrays, strings, hashing"
    if week in (4, 5):
        return "Two pointers, sliding window, stack"
    if week in (6, 7):
        return "Binary search, linked list"
    if week in (8, 9):
        return "Recursion, trees, BST"
    if week in (10, 11):
        return "BFS/DFS, graph basics"
    if week in (12, 13):
        return "Heaps, greedy, intervals"
    if week in (14, 15):
        return "Intro DP (1-D)"
    return "Mixed timed sets, revisit failures"


def phase_of_week(week: int) -> str:
    """VBA PhaseOfWeek -> 'P1'..'P6'."""
    if 1 <= week <= 3:
        return "P1"
    if 4 <= week <= 6:
        return "P2"
    if week in (7, 8):
        return "P3"
    if 9 <= week <= 11:
        return "P4"
    if 12 <= week <= 15:
        return "P5"
    return "P6"


def is_checkpoint_week(week: int) -> bool:
    """VBA IsCheckpointWeek."""
    return week in CHECKPOINT_WEEKS


def day_plan_text(week: int, day_index: int) -> str:
    """VBA DayPlanText.  day_index: 0 = Mon ... 6 = Sun."""
    if week == 1:
        return _WEEK1_DAYS[day_index]
    if week == 2 and day_index == 5:
        return "Build 2 (5h): cron-based backup script with log rotation and a restore test"
    if day_index <= 4:
        return f"{week_focus(week)} | DSA: {week_dsa(week)}"
    if day_index == 5:
        return f"Mini-project / lab (5h): {week_focus(week)}"
    return "Weekly review (P32), update tracker, plan next week, rest"


def day_planned_hours(day_index: int) -> float:
    """Mon-Fri 2.5h, Sat 5h, Sun 2h (from BuildWeeklySheet)."""
    if day_index <= 4:
        return 2.5
    return 5.0 if day_index == 5 else 2.0


# (phase_id, category, item)  - the exact AddTask rows, in sheet order
TASKS: Final[list[tuple[int, str, str]]] = [
    (0, 'Task', "Create GitHub repo 'learning-journal' (README + one folder per phase)"),
    (0, 'Task', 'Copy the roadmap document into the repo (or into Obsidian)'),
    (0, 'Task', 'Confirm Linux setup works (WSL2 Ubuntu or a VM): run lsb_release -a'),
    (0, 'Task', 'Create a free DSA-site account (LeetCode or similar); solve 1 easy problem to test the flow'),
    (0, 'Task', "Read 'How to Use AI for Learning' (Part 7, 15 min)"),
    (0, 'Task', 'Decide weekly study slots and put them in your phone calendar'),
    (0, 'Task', 'Write your real weekly study hours in Goals (shrink or stretch the plan if it is not ~19 hrs/week)'),
    (1, 'Topic', 'Linux: filesystem layout, paths, permissions (chmod/chown), users/groups, processes, systemd, package managers, ssh keys, cron, logs (journalctl, /var/log)'),
    (1, 'Topic', 'Text tools: grep, sed, awk, cut, sort, pipes and redirection'),
    (1, 'Topic', 'Bash: variables, conditionals, loops, functions, exit codes, set -euo pipefail'),
    (1, 'Topic', 'OS concepts: process vs thread, memory, scheduling, deadlock (just the idea)'),
    (1, 'Topic', 'Git: commit, branch, merge, rebase, stash, resolving conflicts, pull-request flow'),
    (1, 'Topic', 'Networking: TCP/IP model, IP, subnet/CIDR, ports, DNS, HTTP/HTTPS/TLS, NAT, firewall, load balancer idea'),
    (1, 'Topic', 'Tools: ping, curl, dig, ss, traceroute'),
    (1, 'Task', 'Task 1 (W1): Filesystem layout, paths, core commands (ls, cd, cp, mv, rm, find, man)'),
    (1, 'Task', 'Task 2 (W1): Users, groups, permissions (chmod, chown, umask), sudo'),
    (1, 'Task', 'Task 3 (W1): Processes and services (ps, top, kill, systemctl, journalctl, apt); install and debug nginx'),
    (1, 'Task', 'Task 4 (W1): Text tools: pipes, redirection, grep, sed, awk, sort, uniq'),
    (1, 'Task', 'Task 5 (W2): Bash scripting: arguments, loops, functions, trap, cron, set -euo pipefail'),
    (1, 'Task', 'Task 6 (W2): SSH keys, scp/rsync, passwordless login to a VM'),
    (1, 'Task', 'Task 7 (W2): OS concepts: process vs thread, memory, scheduling, deadlock (explain back, P07)'),
    (1, 'Task', 'Task 8 (W3): Git: branches, merge, rebase, stash, resolve conflicts, PR workflow'),
    (1, 'Task', 'Task 9 (W3): Networking: TCP/IP model, IP, subnet/CIDR, ports, NAT, firewall'),
    (1, 'Task', 'Task 10 (W3): DNS, HTTP, HTTPS/TLS, load balancer idea'),
    (1, 'Task', 'Collect 10 real job descriptions (Chennai / Bengaluru / remote), highlight repeated keywords, update the gap table (Week 1)'),
    (1, 'Task', 'Resume v1: fix placeholders (CGPA, internship dates), lead with Cloud/DevOps, add GitHub links (Week 2)'),
    (1, 'Build', 'Build 1 (W1): server-health.sh (disk, memory, service, log, exit code) pushed to GitHub with a README'),
    (1, 'Build', 'Build 2 (W2): backup script with cron, log rotation and a restore test'),
    (1, 'Build', "Build 3 (W3): debug an nginx site using only curl, ss, dig and logs; write a one-page 'URL to page' explanation"),
    (1, 'Optional', 'Bonus: subnet 5 CIDR ranges by hand (e.g., /24 into four /26s)'),
    (1, 'Optional', 'Bonus: tcpdump a single curl request and label the packets'),
    (1, 'Exit Test', 'Write a 30-line Bash script from a blank file without AI'),
    (1, 'Exit Test', 'Resolve a merge conflict on a practice repo'),
    (1, 'Exit Test', 'Explain the URL-to-page journey (DNS > TCP > TLS > HTTP) out loud in under 3 minutes'),
    (1, 'Exit Test', 'Explain what chmod 640 means and why'),
    (1, 'Exit Test', 'Answer 6 of the 8 Phase 1 self-check questions without notes'),
    (2, 'Topic', 'Python: types, control flow, functions, collections, comprehensions, OOP basics, exceptions, file I/O, virtualenv, JSON, requests, argparse, logging, type hints, pytest'),
    (2, 'Topic', 'SQL: SELECT/WHERE, JOINs (inner/left), GROUP BY/HAVING, subqueries, constraints, indexes'),
    (2, 'Topic', 'DBMS: normalization (1NF-3NF), transactions, ACID, isolation levels (basic idea), primary/foreign keys'),
    (2, 'Task', 'Python core + data structures'),
    (2, 'Task', 'SQL: joins, grouping, subqueries'),
    (2, 'Task', 'DBMS: normalization, ACID, indexes'),
    (2, 'Task', 'Start applying: 5 applications + 2 referral messages per week (from Week 6)'),
    (2, 'Build', 'Build: Python CLI that parses a log file and prints a summary (errors per hour, top IPs), with tests'),
    (2, 'Build', 'Build: design a small schema (users/orders/products) and write 10 queries against it'),
    (2, 'Exit Test', '15 SQL problems solved (LeetCode or HackerRank SQL)'),
    (2, 'Exit Test', 'Explain an index, why it speeds reads and what it costs on writes'),
    (2, 'Exit Test', 'Explain ACID with a bank-transfer example'),
    (2, 'Exit Test', 'CLI tool has at least 5 passing pytest tests'),
    (3, 'Topic', 'REST: HTTP methods, status codes, idempotency, resource design, JSON'),
    (3, 'Topic', 'FastAPI: routing, Pydantic validation, dependency injection, SQLAlchemy sessions, Alembic migrations, env-var config, structured logging'),
    (3, 'Topic', 'Auth basics (concepts only): password hashing, JWT idea, API keys'),
    (3, 'Topic', 'Testing: unit vs integration, test database, fixtures'),
    (3, 'Task', 'REST design + HTTP status codes'),
    (3, 'Task', 'Tests + migrations'),
    (3, 'Optional', '2-hour React refresher so the front-end resume line stays defensible'),
    (3, 'Build', 'Build: rebuild a small API (tasks or inventory) from a blank folder without copying internship code; add tests and a README with run steps'),
    (3, 'Exit Test', 'Explain every file in your own API without AI'),
    (3, 'Exit Test', 'Explain the difference between PUT and PATCH, and 401 vs 403'),
    (3, 'Exit Test', 'Tests pass locally'),
    (3, 'Exit Test', 'A new migration applies cleanly'),
    (4, 'Topic', 'Containers vs VMs, images and layers, Dockerfile best practices (multi-stage, non-root, .dockerignore), volumes, networks, health checks, Compose'),
    (4, 'Topic', 'Image scanning basics (Trivy), tagging and versioning, registries'),
    (4, 'Topic', 'GitHub Actions: workflow syntax, jobs, matrix, caching, secrets, artifacts, environments, branch protection'),
    (4, 'Topic', 'Deployment strategies: rolling, blue/green, rollback'),
    (4, 'Task', 'Dockerfile best practices (multi-stage, non-root)'),
    (4, 'Task', 'Compose with volumes, networks and health checks'),
    (4, 'Task', 'GitHub Actions pipeline: lint > test > build > scan > push'),
    (4, 'Task', 'Resume v2: add the Phase 3/4 projects (Week 10)'),
    (4, 'Build', 'Build: CI/CD pipeline for the Phase 3 API (lint, test, build image, scan, push; deploy target arrives in Phase 5)'),
    (4, 'Exit Test', 'Explain image layers and why instruction order affects the build cache'),
    (4, 'Exit Test', 'Pipeline fails on a failing test and passes when fixed'),
    (4, 'Exit Test', 'Image runs as non-root, and you can show it'),
    (4, 'Exit Test', 'Explain how you would roll back a bad release'),
    (5, 'Topic', 'Week 12 - Cloud basics + AWS core: IAM, VPC (subnets, route tables, internet gateway, NAT, security groups), EC2, S3, RDS, CloudWatch'),
    (5, 'Topic', 'Week 13 - Terraform on AWS: providers, variables, outputs, remote state in S3, modules, plan/apply, drift'),
    (5, 'Topic', 'Week 14 - Kubernetes basics: pods, deployments, services, ConfigMaps/Secrets, probes, kubectl; practise on kind or minikube'),
    (5, 'Topic', 'Week 15 - Capstone: API on AWS with Terraform, GitHub Actions (OIDC, not stored keys) and monitoring'),
    (5, 'Task', 'AWS account + billing alarm + budget (create the account in Week 11; set the alarm before creating anything)'),
    (5, 'Task', 'AWS core: IAM, VPC, EC2, S3, RDS basics'),
    (5, 'Task', 'Terraform on AWS with remote state'),
    (5, 'Task', 'Kubernetes basics on kind/minikube'),
    (5, 'Optional', "AWS Cloud Practitioner exam (verify the current exam code and fee on AWS's certification page)"),
    (5, 'Build', 'Build: AWS + Terraform capstone deployed with GitHub OIDC CI/CD and monitoring; README, architecture diagram and runbook'),
    (5, 'Build', 'Build: deploy the API to a local Kubernetes cluster'),
    (5, 'Exit Test', 'Explain what a security group does versus a NACL'),
    (5, 'Exit Test', 'Explain Terraform state and why it is stored remotely with locking'),
    (5, 'Exit Test', 'Capstone deployed, reachable, and destroyed cleanly with terraform destroy'),
    (5, 'Exit Test', 'Deploy the API to a local Kubernetes cluster and kill a pod to watch it recover'),
    (6, 'Topic', 'Revise OS, networking and DBMS: write 1-paragraph answers for 40 common questions'),
    (6, 'Topic', "Scenario thinking: 'Site is down, how do you debug?', 'Deployment failed, what next?', 'Disk is 95% full, what do you check?'"),
    (6, 'Topic', 'System design basics: load balancer, caching, DB replication, queues, CDN, health checks; practise a URL shortener and a deployment pipeline'),
    (6, 'Topic', 'Behavioural: 5 STAR stories from the two internships and the Kimai project'),
    (6, 'Task', '40 OS/CN/DBMS answers written'),
    (6, 'Task', "10 scenario answers ('site is down...')"),
    (6, 'Task', '2 system design practices'),
    (6, 'Task', '5 STAR stories'),
    (6, 'Task', '4 mock interviews (AI + a friend); log weak spots'),
    (6, 'Task', 'Resume v3 (add the AWS capstone), reviewed by 2 people'),
    (6, 'Task', 'LinkedIn and GitHub polished (pinned repos with READMEs)'),
    (6, 'Exit Test', 'Explain every project on your resume in 3 minutes each, no notes'),
    (6, 'Exit Test', '4 mock interviews done, weak spots logged in the tracker'),
    (7, 'Task', 'DSA: ~80-100 problems with the re-solve rule (30 min a day on weekdays)'),
    (7, 'Task', 'Job applications tracked weekly (5 per week from Week 6)'),
    (7, 'Task', 'Sunday weekly review done every week (prompt P32)'),
]

import os
from datetime import datetime, timedelta

# Define the file where tasks will be stored
TASK_FILE = 'tasks.txt'
DATE_FORMAT = '%Y-%m-%d %H:%M'  # Define the date format


class Task:
    def __init__(self, name, group, time_commitment, difficulty, deadline_str):
        self.name = name
        self.group = group.lower()
        self.time_commitment = int(time_commitment)
        self.difficulty = int(difficulty)
        self.deadline_str = deadline_str.strip()
        # Convert deadline string to datetime object
        self.deadline = datetime.strptime(self.deadline_str, DATE_FORMAT)
        # Calculate time till deadline in seconds
        self.time_till_deadline = (self.deadline - datetime.now()).total_seconds()
        self.group_score = self.get_group_score()

    def get_group_score(self):
        if self.group == 'school':
            return 0
        elif self.group == 'work':
            return 1
        else:  # 'extra' group or any other group
            return 2

    def time_left_str(self):
        # Calculate time left as a timedelta object
        time_left = self.deadline - datetime.now()
        if time_left.total_seconds() < 0:
            return "Overdue"
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if not parts:
            parts.append("Less than a minute")
        return ', '.join(parts) + " left"

    def __repr__(self):
        time_left = self.time_left_str()
        return (f"{self.name} | {self.group.capitalize()} | Time: {self.time_commitment}h | "
                f"Difficulty: {self.difficulty} | Deadline: {self.deadline_str} "
                f"({time_left})")


def load_tasks():
    tasks = []
    if os.path.exists(TASK_FILE):
        with open(TASK_FILE, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) == 5:
                    name, group, time_commitment, difficulty, deadline_str = parts
                    tasks.append(Task(name.strip(), group.strip(), time_commitment.strip(), difficulty.strip(),
                                      deadline_str.strip()))
    return tasks


def save_tasks(tasks):
    with open(TASK_FILE, 'w') as f:
        for task in tasks:
            f.write(f"{task.name} | {task.group} | {task.time_commitment} | {task.difficulty} | {task.deadline_str}\n")


def prioritize_tasks(tasks):
    # Update group score and time till deadline
    for task in tasks:
        task.group_score = task.get_group_score()
        task.time_till_deadline = (task.deadline - datetime.now()).total_seconds()

    def difficulty_sort_value(task):
        if task.time_commitment <= 2:
            return task.difficulty  # Lower difficulty first
        else:
            return -task.difficulty  # Higher difficulty first

    # Sort tasks based on (group_score, time_till_deadline, -time_commitment, difficulty_sort_value)
    tasks.sort(key=lambda x: (x.group_score, x.time_till_deadline, -x.time_commitment, difficulty_sort_value(x)))


def schedule_tasks(tasks):
    # Initialize the calendar for the next two weeks
    calendar = {}
    today = datetime.now().date()
    end_date = today + timedelta(days=13)  # Next two weeks

    for day in (today + timedelta(days=i) for i in range(14)):
        calendar[day] = {'available_hours': 6, 'tasks': []}

    unscheduled_tasks = set()  # Keep track of tasks that couldn't be scheduled

    # Schedule tasks in order of priority
    for task in tasks:
        remaining_time = task.time_commitment
        # Exclude the day of the deadline from scheduling
        last_day = task.deadline.date() - timedelta(days=1)
        days_left = (last_day - today).days + 1  # Include today
        if days_left <= 0:
            print(f"Task '{task.name}' cannot be scheduled as there are no days left before the deadline.")
            unscheduled_tasks.add(task)
            continue

        # Get the list of dates available before the deadline (excluding the deadline day)
        available_dates = [day for day in calendar.keys() if today <= day <= last_day]

        if task.time_commitment <= 2:
            # Try to schedule it on a single day
            scheduled = False
            for day in available_dates:
                if calendar[day]['available_hours'] >= task.time_commitment:
                    # Enough time available, schedule the task
                    calendar[day]['tasks'].append((task, task.time_commitment))
                    calendar[day]['available_hours'] -= task.time_commitment
                    scheduled = True
                    break
                else:
                    # Try to free up time by removing lower-priority tasks
                    needed_time = task.time_commitment - calendar[day]['available_hours']
                    # Find lower-priority tasks on that day
                    removable_tasks = []
                    for scheduled_task, hours in calendar[day]['tasks']:
                        if scheduled_task.group_score > task.group_score:
                            removable_tasks.append((scheduled_task, hours))
                    # Total time that can be freed
                    freed_time = sum(hours for _, hours in removable_tasks)
                    if freed_time >= needed_time:
                        # Remove lower-priority tasks
                        for removed_task, hours in removable_tasks:
                            calendar[day]['tasks'].remove((removed_task, hours))
                            calendar[day]['available_hours'] += hours
                            unscheduled_tasks.add(removed_task)
                        # Now schedule the current task
                        calendar[day]['tasks'].append((task, task.time_commitment))
                        calendar[day]['available_hours'] -= task.time_commitment
                        scheduled = True
                        break
            if not scheduled:
                print(f"Cannot schedule task '{task.name}' even after removing lower-priority tasks.")
                unscheduled_tasks.add(task)
        else:
            # Break task into chunks to finish by the day before deadline
            for day in available_dates:
                if remaining_time <= 0:
                    break
                allocation = min(remaining_time, calendar[day]['available_hours'])
                if allocation > 0:
                    calendar[day]['tasks'].append((task, allocation))
                    calendar[day]['available_hours'] -= allocation
                    remaining_time -= allocation
                else:
                    # Try to free up time by removing lower-priority tasks
                    needed_time = min(remaining_time, 6) - calendar[day]['available_hours']
                    # Find lower-priority tasks on that day
                    removable_tasks = []
                    for scheduled_task, hours in calendar[day]['tasks']:
                        if scheduled_task.group_score > task.group_score:
                            removable_tasks.append((scheduled_task, hours))
                    freed_time = sum(hours for _, hours in removable_tasks)
                    if freed_time >= needed_time:
                        # Remove lower-priority tasks
                        for removed_task, hours in removable_tasks:
                            calendar[day]['tasks'].remove((removed_task, hours))
                            calendar[day]['available_hours'] += hours
                            unscheduled_tasks.add(removed_task)
                        # Now schedule the current task
                        allocation = min(remaining_time, calendar[day]['available_hours'])
                        calendar[day]['tasks'].append((task, allocation))
                        calendar[day]['available_hours'] -= allocation
                        remaining_time -= allocation
            if remaining_time > 0:
                print(
                    f"Cannot fully schedule task '{task.name}' even after removing lower-priority tasks. Remaining time: {remaining_time}h")
                unscheduled_tasks.add(task)

    # After scheduling, collect the tasks that are in unscheduled_tasks set
    if unscheduled_tasks:
        unscheduled_task_names = ', '.join([f"'{task.name}'" for task in unscheduled_tasks])
        print(
            f"\nATTENTION ATTENTION - {unscheduled_task_names} cannot be scheduled, either delete task or extend deadline for {unscheduled_task_names}")

    return calendar


def display_calendar(calendar):
    print("\nSchedule for the Next Two Weeks:")
    print("--------------------------------")
    days = list(calendar.keys())
    days.sort(reverse=True)
    for day in days:
        date_str = day.strftime('%d %b %a')
        print(f"\n{date_str}:")
        if calendar[day]['tasks']:
            for task, hours in calendar[day]['tasks']:
                print(f"- {task.name} ({task.group.capitalize()}) - {hours}h")
        else:
            print("No tasks scheduled.")
    print()


def display_tasks(tasks):
    if not tasks:
        print("\nNo tasks to display.\n")
        return
    print("\nPrioritized Task List:")
    print("----------------------")
    for idx, task in enumerate(tasks, 1):
        print(f"{idx}. {task}")
    print()


def add_task(tasks):
    name = input("Enter task name: ").strip()
    group = input("Enter group ('school', 'work', or 'extra'): ").strip().lower()
    while group not in ['school', 'work', 'extra']:
        group = input("Invalid group. Please enter 'school', 'work', or 'extra': ").strip().lower()
    time_commitment = input("Enter time commitment in hours (integer): ").strip()
    while not time_commitment.isdigit():
        time_commitment = input("Invalid input. Enter time commitment in hours (integer): ").strip()
    difficulty = input("Enter difficulty (integer): ").strip()
    while not difficulty.isdigit():
        difficulty = input("Invalid input. Enter difficulty (integer): ").strip()
    deadline_str = input(f"Enter deadline (format {DATE_FORMAT}): ").strip()
    while True:
        try:
            deadline = datetime.strptime(deadline_str, DATE_FORMAT)
            if deadline <= datetime.now():
                print("Deadline must be a future date and time.")
                deadline_str = input(f"Enter deadline (format {DATE_FORMAT}): ").strip()
                continue
            break
        except ValueError:
            deadline_str = input(f"Invalid date format. Enter deadline (format {DATE_FORMAT}): ").strip()
    new_task = Task(name, group, time_commitment, difficulty, deadline_str)
    tasks.append(new_task)
    save_tasks(tasks)
    print("Task added successfully.\n")


def delete_task(tasks):
    if not tasks:
        print("No tasks to delete.\n")
        return
    display_tasks(tasks)
    choice = input("Enter the number of the task to delete (or 'c' to cancel): ").strip()
    if choice.lower() == 'c':
        return
    while not choice.isdigit() or not (1 <= int(choice) <= len(tasks)):
        choice = input("Invalid choice. Enter a valid task number to delete: ").strip()
    idx = int(choice) - 1
    removed_task = tasks.pop(idx)
    save_tasks(tasks)
    print(f"Task '{removed_task.name}' deleted successfully.\n")


def main():
    tasks = load_tasks()
    while True:
        # Update time till deadline for each task
        for task in tasks:
            task.time_till_deadline = (task.deadline - datetime.now()).total_seconds()
        prioritize_tasks(tasks)
        calendar = schedule_tasks(tasks)
        display_calendar(calendar)
        display_tasks(tasks)
        print("Options:")
        print("[A] Add a task")
        print("[D] Delete a task")
        print("[Q] Quit")
        choice = input("Enter your choice: ").strip().lower()
        if choice == 'a':
            add_task(tasks)
        elif choice == 'd':
            delete_task(tasks)
        elif choice == 'q':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please select A, D, or Q.\n")


if __name__ == "__main__":
    main()

from collections import defaultdict
import random
from tabulate import tabulate

timeslots = [
    510,   # 8:30 AM
    525,   # 8:45 AM
    540,   # 9:00 AM
    555,   # 9:15 AM
    570,   # 9:30 AM
    585,   # 9:45 AM
    600,   # 10:00 AM
    615,   # 10:15 AM
    630,   # 10:30 AM
    645,   # 10:45 AM
    660,   # 11:00 AM
    675,   # 11:15 AM
    690,   # 11:30 AM
    705,   # 11:45 AM
    720,   # 12:00 PM
    735,   # 12:15 PM
    750,   # 12:30 PM
    765,   # 12:45 PM
    780,   # 1:00 PM 
    795,   # 1:15 PM 
    810,   # 1:30 PM 
    825,   # 1:45 PM 
    840,   # 2:00 PM 
    855,   # 2:15 PM 
    870,   # 2:30 PM 
    885,   # 2:45 PM
    900,   # 3:00 PM
    915,   # 3:15 PM
    930,   # 3:30 PM
    945,   # 3:45 PM
    960,   # 4:00 PM
]

class Timetable:
    def __init__(self, genes):
        self.genes = genes
        self.conflict = 0
        self.fitness = self.calculate_fitness()

    def calculate_fitness(self):
        total_penalty = 0
        total_conflict = 0

        student_schedule = defaultdict(lambda: defaultdict(list))
        instructor_schedule = defaultdict(lambda: defaultdict(list))
        class_schedule = defaultdict(lambda: defaultdict(list))

        for gene in self.genes:
            section, day, timeslot_idx, classroom = gene

            total_students = section['total_students']

            # Check classroom capacity
            if classroom['capacity'] < total_students:
                total_penalty += 100
                total_conflict += 1

            for intake_id in section['intake_ids']:
                student_schedule[intake_id][day].append((timeslots[timeslot_idx], timeslots[timeslot_idx] + section['duration']))
            instructor_schedule[section['instructor_id']][day].append((timeslots[timeslot_idx], timeslots[timeslot_idx] + section['duration']))
            class_schedule[classroom['id']][day].append((timeslots[timeslot_idx], timeslots[timeslot_idx] + section['duration']))

        for schedule in [student_schedule, instructor_schedule, class_schedule]:
            for days in schedule.values():
                for slots in days.values():
                    slots.sort()

        # Calculate penalties and conflicts for student_schedule
        penalty, conflict = self.check_schedule_conflicts(student_schedule, True, True)
        total_penalty += penalty
        total_conflict += conflict

        # Calculate penalties and conflicts for instructor_schedule
        penalty, conflict = self.check_schedule_conflicts(instructor_schedule, False, False)
        total_penalty += penalty
        total_conflict += conflict

        # Calculate penalties and conflicts for class_schedule
        penalty, conflict = self.check_schedule_conflicts(class_schedule, False, False)
        total_penalty += penalty
        total_conflict += conflict

        # self.fitness = 100 - penalty
        self.conflict = total_conflict
        return 100 / (100 + total_penalty)
    
    def check_schedule_conflicts(self, schedule, check_gaps, check_boundaries):
        penalty = 0
        conflict = 0
        end_of_day_time = 1020
        start_of_day_time = 600

        for _, days in schedule.items():
            for _, slots in days.items():
                # Check for boundary violations if the check_boundaries flag is set
                if check_boundaries:
                    if slots[-1][1] > end_of_day_time:
                        penalty += (slots[-1][1] - end_of_day_time) // 5

                    # Penalty for first class start before 10am
                    if slots[0][0] < start_of_day_time:
                        # print((start_of_day_time - slots[0][0]) // 5, slots[0][0])
                        penalty += (start_of_day_time - slots[0][0]) // 5

                if len(slots) <= 1:
                    continue

                for i in range(len(slots) - 1):
                    current_slot = slots[i]
                    next_slot = slots[i + 1]

                    current_end = current_slot[1]
                    next_start = next_slot[0]

                    # Check for overlapping time slots
                    if current_end > next_start:
                        penalty += 100
                        conflict += 1

                    if check_gaps and next_slot:
                        gap = next_start - current_end
                        # Penalty for too short or too long gaps between classes
                        # if gap < 15:  
                        #     penalty += 0
                        if gap < 15 or gap > 120:
                            penalty += 100
                            conflict += 1

        return penalty, conflict
        
    def get_instructor_schedule(self):
        # Initialize a dictionary to hold the instructor schedule
        instructor_schedule = defaultdict(lambda: defaultdict(list))

        # Populate the instructor schedule directly from genes
        for gene in self.genes:
            section, day, timeslot_idx, classroom = gene

            instructor_id = section['instructor_id']

            start_time = self.convert_minutes_to_time(timeslots[timeslot_idx])
            end_time = self.convert_minutes_to_time(timeslots[timeslot_idx] + section['duration'])
            time_slot_str = f"{start_time} - {end_time}"
            instructor_slot = {
                'section_id': section['id'],
                'time_slot_str': time_slot_str
            }

            instructor_schedule[instructor_id][day].append(instructor_slot)

        # Collect the timetable in a structured format
        output = []
        for instructor_id, schedule in instructor_schedule.items():
            for day, entries in schedule.items():
                day_name = self.get_day_name(day)
                for entry in entries:
                    section_id = entry['section_id']
                    time_slot_str = entry['time_slot_str']
                    output.append({
                        'instructor_id': instructor_id,
                        'day': day_name,
                        'section_id': section_id,
                        'time': time_slot_str
                    })
        return output

    def get_class_availability(self):
        # Initialize a dictionary to hold the class schedule
        class_schedule = defaultdict(lambda: defaultdict(list))

        # Populate the class schedule directly from genes
        for gene in self.genes:
            section, day, timeslot_idx, classroom = gene

            start_time = self.convert_minutes_to_time(timeslots[timeslot_idx])
            end_time = self.convert_minutes_to_time(timeslots[timeslot_idx] + section['duration'])
            time_slot_str = f"{start_time} - {end_time}"

            class_slot = {
                'section_id': section['id'],
                'time_slot_str': time_slot_str
            }

            class_schedule[classroom['id']][day].append(class_slot)

        # Collect the timetable in a structured format
        output = []
        for classroom_id, schedule in class_schedule.items():
            for day, entries in schedule.items():
                day_name = self.get_day_name(day)
                for entry in entries:
                    section_id = entry['section_id']
                    time_slot_str = entry['time_slot_str']
                    output.append({
                        'classroom_id': classroom_id,
                        'day': day_name,
                        'section_id': section_id,
                        'time': time_slot_str
                    })
        return output

    def get_student_timetable(self):
        # Initialize a dictionary to hold the schedule
        student_schedule = defaultdict(lambda: defaultdict(list))

        # Populate the student schedule directly from genes
        for gene in self.genes:
            section, day, timeslot_idx, classroom = gene

            for intake_id in section['intake_ids']:
                start_time = self.convert_minutes_to_time(timeslots[timeslot_idx])
                end_time = self.convert_minutes_to_time(timeslots[timeslot_idx] + section['duration'])
                time_slot_str = f"{start_time} - {end_time}"

                student_slot = {
                    'section_id': section['id'],
                    'classroom_id': classroom['id'],
                    'time_slot_str': time_slot_str
                }
                student_schedule[intake_id][day].append(student_slot)

        # Collect the timetable in a structured format
        output = []
        for intake_id, schedule in student_schedule.items():
            for day, time_slots in schedule.items():
                day_name = self.get_day_name(day)
                for slot in time_slots:
                    section_id = slot['section_id']
                    classroom_id = slot['classroom_id']
                    time_slot_str = slot['time_slot_str']
                    output.append({
                        'intake_id': intake_id,
                        'day': day_name,
                        'section_id': section_id,
                        'classroom_id': classroom_id,
                        'time': time_slot_str
                    })
        return output

    def get_all_slots(self):
        slots = []
        for gene in self.genes:
            section, day, timeslot_idx, classroom = gene

            for intake_id in section['intake_ids']:
                slot = {
                    'intake_id': intake_id,
                    'section_id': section['id'],
                    'instructor_id': section['instructor_id'],
                    'classroom_id': classroom['id'],
                    'start_time': self.convert_minutes_to_time(timeslots[timeslot_idx]),
                    'end_time': self.convert_minutes_to_time(timeslots[timeslot_idx] + section['duration']),
                    'day': self.get_day_name(day)
                }
                slots.append(slot)
        return slots

    def get_day_name(self, day):
        if day == 1:
            return "Monday"
        elif day == 2:
            return "Tuesday"
        elif day == 3:
            return "Wednesday"
        elif day == 4:
            return "Thursday"
        elif day == 5:
            return "Friday"
        else:
            return "Unknown"

    def convert_minutes_to_time(self, minutes):
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02}:{mins:02}"

class GeneticAlgorithm:
    def __init__(self, population_size, gene_length, mutation_rate, sections, classrooms):
        self.population_size = population_size
        self.num_parents = int(0.1 * self.population_size)
        self.gene_length = gene_length
        self.mutation_rate = mutation_rate
        self.stagnation_threshold = 10
        self.sections = sections
        self.classrooms = classrooms
        self.population = self.initialize_population()
        self.best_fitness_history = []

    def initialize_population(self):
        population = []
        for _ in range(self.population_size):
            genes = self.generate_genes(self.sections, self.classrooms)
            population.append(Timetable(genes)) 
        return population

    def generate_genes(self, sections, classrooms):
        genes = []
        for section in sections:
            timeslot_idx = random.randint(0, len(timeslots) - 1)
            selected_day = random.randint(1, 5)
            selected_classroom = random.choice(classrooms)
            genes.append((section, selected_day, timeslot_idx, selected_classroom))
        return genes
    
    def mutate(self, genes, sections, classrooms):
        if random.random() < self.mutation_rate:
            i = random.randint(0, len(genes) - 1)

            section = sections[i]
            timeslot_idx = random.randint(0, len(timeslots) - 1)
            selected_day = random.randint(1, 5)
            selected_classroom = random.choice(classrooms)

            genes[i] = (section, selected_day, timeslot_idx, selected_classroom)
        return genes

    def crossover(self, parent1, parent2):
        child_genes = [
            parent1.genes[i] if random.random() < 0.5 else parent2.genes[i]
            for i in range(self.gene_length)
        ]
        return Timetable(self.mutate(child_genes, self.sections, self.classrooms))

    def select_parent(self):
        tournament_size = 3
        tournament = random.sample(self.population, tournament_size)
        tournament.sort(key=lambda x: x.fitness, reverse=True)
        return tournament[0]

    def evolve(self):
        new_population = []
        # Preserve the best individuals (elitism)
        elitism_size = int(0.1 * self.population_size)
        elites = sorted(self.population, key=lambda x: x.fitness, reverse=True)[:elitism_size]
        new_population.extend(elites)

        for _ in range(self.population_size - elitism_size):
            parent1 = self.select_parent()
            parent2 = self.select_parent()
            child = self.crossover(parent1, parent2)
            new_population.append(child)

        self.population = new_population

    def adjust_mutation_rate(self):
        if len(self.best_fitness_history) >= self.stagnation_threshold:
            if self.best_fitness_history[-1] == max(self.best_fitness_history[-self.stagnation_threshold:]):
                self.mutation_rate = min(0.5, self.mutation_rate * 1.05)  # Increase mutation rate if max fitness are the same
                print(f'Rate increased:{self.mutation_rate}')
            else:
                self.mutation_rate = max(0.1, self.mutation_rate * 0.95)  # Decrease mutation rate
                print(f'Rate decreased:{self.mutation_rate}')
        else:
            self.mutation_rate = max(0.1, self.mutation_rate * 0.95)  # Decrease mutation rate if no stagnation
            print(f'Rate decreased:{self.mutation_rate}')

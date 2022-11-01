
import xlsxwriter

from jarvis.abilities.timekeeper.ability import TimeKeeper
from jarvis.abilities.timekeeper.models import WorkShift, Project

year = int(input("Which year do you want to export? "))
month = int(input("Which month do you want to export? "))
project_name = input("Which project? ")
timekeeper_ability = TimeKeeper()

workbook = xlsxwriter.Workbook(f"{year}_{month}.xlsx")
worksheet = workbook.add_worksheet()
current_day = None
row = 0
bold = workbook.add_format({'bold': True})
workshifts_for_current_day = []
project = Project.objects.try_get(name=project_name)

if project is None:
    print("Project not found:", project_name)
    exit(-1)

work_shifts = WorkShift.objects.filter(month=month,
                                       year=year,
                                       project=project).all()

for work_shift in work_shifts:
    beginning_date = work_shift.beginning.date()
    duration = work_shift.duration
    hours, minutes, seconds = duration.hour, duration.minute, duration.second

    if beginning_date != current_day:
        current_day = beginning_date

        billable_hours = timekeeper_ability.get_total_billable_hours(
            *workshifts_for_current_day)
        workshifts_for_current_day = []

        sum_string = "Totalt arbetade timmar denna dag:"
        worksheet.write(row, 0, sum_string)
        worksheet.write(row, 1, billable_hours)
        row += 1
        worksheet.write(row, 0, "")
        row += 1
        worksheet.write(row, 0, beginning_date.strftime("%Y-%m-%d"), bold)
        row += 1

    duration_string = f"Från {work_shift.beginning.strftime('%H:%M')} " \
                      f"till {work_shift.end.strftime('%H:%M')} " \
                      f"({hours} timmar, {minutes} " \
                      f"minuter, {seconds} sekunder)"

    workshifts_for_current_day.append(work_shift)
    worksheet.write(row, 0, duration_string)
    row += 1

billable_hours = timekeeper_ability.get_total_billable_hours(
            *workshifts_for_current_day)
sum_string = "Totalt arbetade timmar denna dag:"
worksheet.write(row, 0, sum_string)
worksheet.write(row, 1, billable_hours)

all_sum = timekeeper_ability.get_total_billable_hours(*work_shifts)
worksheet.write(row + 2, 0,
                "Totalt arbetade timmar under perioden:", bold)
worksheet.write(row + 2, 1, all_sum, bold)
worksheet.write(0, 0, "")
workbook.close()

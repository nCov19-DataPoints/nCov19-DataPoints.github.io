import math
import numpy as np
import scipy.integrate
import scipy.optimize
import matplotlib.pyplot as plt
import matplotlib.widgets  # Cursor
import datetime

incubationPeriod = 5.2
e_to_i = 1.0 / incubationPeriod  # The rate at which an exposed person becomes infective (incubation period). Note that people are and can only be tested if they have symptoms, so they are not discovered by tests before that.
timeDiagnosedToResistant = 10.0  # The rate a diagnosed recovers and moves into the resistant phase.
timeDiagnosedToDeath = 12
icuRate = 0.02
timeInHospital = 12

germany = {
    # Date when Health Minister said "Infection chains are no longer traceable"
    # 14th-16th of March (Day 26-28): Closing of schools
    # 22nd of March (Day 34): General restrictions to meet in public (the week before various restrictions depending on the individual Länder)
    "start_date": datetime.datetime.strptime("15.02.2020", "%d.%m.%Y"),
    "confirmed_cases": [
        17, 17, 17, 17, 17, 18, 18, 18, 30, 33, 35, 43, 65, 106, 126, 159, 199, 265, 408, 586, 758, 891, 978, 1303,
        1868, 2573, 3516, 4883, 6149, 7046, 8968, 11825, 15148, 18846, 22565, 25603, 27746, 30908, 34527, 36471
    ],
    "deaths": [
        0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 4, 5, 7, 7, 10, 12, 17, 22, 32, 40, 44, 57, 72, 95,
        111, 144, 152, 164, 182, 192, 197
    ],
    "dayToStartLeastSquares": 8,
    "noSymptoms": 0.7,
    "I0": 0,  # Guess - the 17 were all in the resitant category at this point ( or diagnosed)
    "daysToModel": 100,
    "lockdown": 35,
    "length_of_lockdown": 50,
    "beta0": 1.0 / 0.5,
    "beta1": 1.0 / 20.0,
    "beta2": 1.0 / 4.0,
    "intensiveUnits": 28000,
    "population": 81E6,

    # Day 8-20 relatively stable growth with 33%
    # A stable growth of 33% means a doubling every 2.4 days!
    # That means a R0 of 8!!
    # Day 22 visible deviation of exponential growth
}
germany["E0"] = germany["I0"] * 3 + 23
germany["R0"] = 16

italy = {
    # Start date determined by first death - 14 days
    "start_date": datetime.datetime.strptime("07.02.2020", "%d.%m.%Y"),
    "confirmed_cases": [
        3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 20, 62, 155, 229, 322, 453, 655, 888, 1128, 1694, 2036, 2502, 3089,
        3858, 4636, 5883, 7375, 9172, 10149, 12462, 12462, 17660, 21157, 24747, 27980, 31506, 35713, 41035, 47021,
        53578, 59138, 63927, 69176, 74386
    ],
    "deaths": [
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 7, 10, 12, 17, 21, 29, 34, 52, 79, 107, 148, 197, 233, 366,
        463, 631, 827, 827, 1266, 1441, 1809, 2158, 2503, 2978, 3405, 4032, 4825, 5476, 6077, 6820, 7503
    ],
    "dayToStartLeastSquares": 16,
    "noSymptoms": 0.9,
    "I0": 200,  # 1 death two weeks later
    "E0": 200 * 10,
    "R0": 0,
    "daysToModel": 100,
    "lockdown": 28,
    "length_of_lockdown": 60,
    "beta0": 1.0 / 1.2,
    "beta1": 1.0 / 20.0,
    "beta2": 1.0 / 4.0,
    "intensiveUnits": 7000,
    "population": 60E6
}

dataset = germany

if len(dataset["confirmed_cases"]) != len(dataset["deaths"]):
    print(str(len(dataset["confirmed_cases"])) + '=len(dataset["confirmed_cases"]) != len(dataset["deaths"])=' + str(
        len(dataset["deaths"])))
    exit(1)

for i in range(0, len(dataset["confirmed_cases"])):
    dataset["confirmed_cases"][i] = dataset["confirmed_cases"][i] - dataset["R0"]
dataset["D0"] = dataset["confirmed_cases"][0]  # must be true for consistency
dataset["T0"] = dataset["deaths"][0]  # must be true for consistency

logPlot = True

population = int(dataset["population"])

daysToModel = dataset["daysToModel"]  # total days to model
E0 = dataset["E0"]  # exposed at initial time step
D0 = dataset["D0"]
I0 = dataset["I0"]
R0 = dataset["R0"]
T0 = dataset["T0"]
RealD = np.asarray(dataset["confirmed_cases"])
RealT = np.asarray(dataset["deaths"])
daysOfData = len(RealD)
RealX = np.arange(daysOfData)
D_to_T = RealT[-1] / np.sum(np.asarray(RealD[0:int(-timeDiagnosedToDeath / 2)]))
D_to_R = 1.0 / 15.0
I_to_R = 0.0

# Parameters set by external data
noSymptoms = dataset[
    "noSymptoms"]  # https://www.reddit.com/r/COVID19/comments/ffzqzl/estimating_the_asymptomatic_proportion_of_2019/
intensiveUnits = dataset["intensiveUnits"]  # ICU units available
daysBeginLockdown = dataset["lockdown"]  # days before lockdown measures (there probably should be several of those)
daysEndLockdown = daysBeginLockdown + dataset[
    "length_of_lockdown"]  # days before lockdown measures are relaxed (there probably should be several of those)
beta0 = dataset[
    "beta0"]  # The parameter controlling how often a susceptible-infected contact results in a new infection.
beta1 = dataset["beta1"]  # beta0 is used during days0 phase, beta1 after days0
Beta2 = dataset["beta2"]

type_individual = np.dtype([
    ('day_exposed', np.int),
    ('day_infectious', np.int),
    ('day_diagnosed', np.int),
    ('day_hospitalized', np.int),
    ('day_recovered', np.int),
    ('day_died', np.int)
])

type_statsperday = np.dtype([
    ('S', np.int),
    ('E', np.int),
    ('I', np.int),
    ('D', np.int),
    ('H', np.int),
    ('R', np.int),
    ('T', np.int)
])

RG = np.random.default_rng()

incubationPeriodValues = np.array([          2,  3,  4,  5,   6,   7,   8,   9,  10,   11,   12,   13,   14])
incubationPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])

infectiousPeriodValues = np.array([          2,  3,  4,  5,   6,   7,   8,   9,  10,   11,   12,   13,   14])
infectiousPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])

probabilityHospital = 0.2
diagToHospitalPeriodValues = np.array([          2,  3,  4,  5,   6,   7,   8,   9,  10,   11,   12,   13,   14])
diagToHospitalPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])
probabilityDeadAfterHospital = 0.1
hospitalToDeadPeriodValues = np.array([         10, 11, 12, 13,  14,  15,  16,  17,  18,   19,   20,   21,   22])
hospitalToDeadPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])
hospitalToRecoveredPeriodValues = np.array([         20, 21, 22, 23,   24,  25,  26,  27,  28,   29,   30,   31,   32])
hospitalToRecoveredPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])

diagToRecoveredPeriodValues = np.array([         7,  8,   9,  10,  11,  12,  13,  14])
diagToRecoveredPeriodProbabilities = np.array([0.4,0.35,0.12,0.06,0.03,0.02,0.01,0.01])

def createExposed(day_exposed):
    day_infectious = day_exposed+RG.choice(incubationPeriodValues, p=incubationPeriodProbabilities)
    day_diagnosed = day_infectious+RG.choice(infectiousPeriodValues, p=infectiousPeriodProbabilities)
    if RG.random()< probabilityHospital:
        day_hospitalized = day_diagnosed+RG.choice(diagToHospitalPeriodValues, p=diagToHospitalPeriodProbabilities)
        if RG.random()< probabilityDeadAfterHospital:
            day_died = day_hospitalized+RG.choice(hospitalToDeadPeriodValues, p=hospitalToDeadPeriodProbabilities)
            day_recovered = daysToModel * 1000
        else:
            day_recovered = day_hospitalized+RG.choice(hospitalToRecoveredPeriodValues, p=hospitalToRecoveredPeriodProbabilities)
            day_died = daysToModel * 1000
    else:
        day_hospitalized = daysToModel * 1000
        day_recovered = day_diagnosed+RG.choice(diagToRecoveredPeriodValues, p=diagToRecoveredPeriodProbabilities)
        day_died = daysToModel * 1000
    a = np.array([(day_exposed, day_infectious, day_diagnosed, day_hospitalized, day_recovered, day_died)], type_individual)
    return a[0]

def calcStatsPerDay(R, T, pop, day):
    # There is probably a more efficient way of doing that?
    E = np.count_nonzero(pop['day_exposed']<=day)
    I = np.count_nonzero(pop['day_infectious']<=day)
    D = np.count_nonzero(pop['day_diagnosed']<=day)
    H = np.count_nonzero(pop['day_hospitalized']<=day)

    S = population - E - R - T
    E = E - I
    I = I - D
    D = D - H

    return np.array([(S,E,I,D,H,R,T)], type_statsperday)[0]


def advanceDay(S,R,T,day,pop):
    # One infected person will generate beta * S / population new
    # exposed people in a time step.
    I = np.count_nonzero(np.logical_and(pop['day_infectious'] <= day, pop['day_diagnosed'] > day))
    popR = np.logical_and(pop['day_recovered']<=day,pop['day_recovered']>=0)
    popT = np.logical_and(pop['day_died']<=day,pop['day_died']>=0)
    dR = np.count_nonzero(popR)
    dT = np.count_nonzero(popT)

    newexposed = []
    beta = beta0 if day < daysBeginLockdown else beta1 if day <= daysEndLockdown else Beta2
    prob = beta * S / population
    for i in range(0, I):
        f =  RG.random()
        if f <= prob:
            newexposed.append(createExposed(day))

    npop = pop[np.logical_not(np.logical_or(popR, popT))]
    npop = np.append(npop, np.array(newexposed, type_individual))
    dS = -len(newexposed)

    return S+dS,R+dR,T+dT,npop

exposed = createExposed(0)
pop = np.full(10, exposed, type_individual)

statsperday = np.zeros(daysToModel, type_statsperday)
statsperday[0] = calcStatsPerDay(0, 0, pop, 0)

S = statsperday[0]['S']
R = statsperday[0]['R']
T = statsperday[0]['T']
print(statsperday[0])
for day in range(1, daysToModel):
    #pop = advanceDay(statsperday[day-1]['S'], day, pop, beta0)
    #statsperday[day] = calcStatsPerDay(pop, day)
    S, R, T, pop = advanceDay(S, R, T, day, pop)
    statsperday[day] = calcStatsPerDay(R, T, pop, day)
print(statsperday)


# Plot
fig = plt.figure(dpi=75, figsize=(20,16))
ax = fig.add_subplot(111)
if logPlot:
    ax.set_yscale("log", nonposy='clip')


X = np.arange(0, daysToModel)
I = statsperday['I']
D = statsperday['D']
R = statsperday['R']
T = statsperday['T']

ax.plot(X, I, 'b', alpha=0.5, lw=1, label='Infectious')
ax.plot(X, D, 'g', alpha=0.5, lw=1, label='Diagnosed and isolated')
ax.plot(X, np.cumsum(D), 'm', alpha=0.5, lw=1, label='Cumulative diagnosed and isolated')
#ax.plot(RealX[dayToStartLeastSquares:], RealD[dayToStartLeastSquares:], 'r', alpha=0.5, lw=1, label='Confirmed cases')
ax.plot(X, R, 'y', alpha=0.5, lw=1, label='Recovered with immunity')
ax.plot(X, T, 'k', alpha=0.5, lw=1, label='Deaths')
#ax.plot(RealX[dayToStartLeastSquares:], RealT[dayToStartLeastSquares:], 'c', alpha=0.5, lw=1, label='Confirmed deaths')

ax.set_xlabel('Time /days')
ax.set_ylabel('Number (1000s)')
ax.set_ylim(bottom=1.0)

ax.grid(linestyle=':')  #b=True, which='major', c='w', lw=2, ls='-')
legend = ax.legend(title='COVID-19 SEIR model'+
                   ' %dk' % (population / 1000) + ' (beta)')
legend.get_frame().set_alpha(0.5)
for spine in ('top', 'right', 'bottom', 'left'):
    ax.spines[spine].set_visible(False)
cursor = matplotlib.widgets.Cursor(ax, color='black', linewidth=1 )
plt.show()
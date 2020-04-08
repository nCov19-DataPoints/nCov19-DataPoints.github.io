import math
import numpy as np
import scipy.integrate
import scipy.optimize
import matplotlib.pyplot as plt
import matplotlib.widgets  # Cursor
import matplotlib.ticker # Locator
import matplotlib.dates  # Ticks
import datetime
import multiprocessing

# NEXT:
# Get the numbers for Austria and run it with that. Similar to Germany, should allow to figure out the coefficient for the lock-down period.
# Then run Italy again, followed by UK
# Try to compare hospital numbers with real stats.
# Compare with healthdata.org


incubationPeriod = 5.2
e_to_i = 1.0 / incubationPeriod  # The rate at which an exposed person becomes infective (incubation period). Note that people are and can only be tested if they have symptoms, so they are not discovered by tests before that.
timeDiagnosedToResistant = 10.0  # The rate a diagnosed recovers and moves into the resistant phase.
timeDiagnosedToDeath = 12
icuRate = 0.02
timeInHospital = 12
probabilityNoSymptoms = 0.5
maxNumSocialBehaviourChanges = 4
maxInfectiousPeriod = 20

germany = {
    # Date when Health Minister said "Infection chains are no longer traceable"
    # 14th-16th of March (Day 26-28): Closing of schools
    # 22nd of March (Day 34): General restrictions to meet in public (the week before various restrictions depending on the individual Länder)
    "start_date": datetime.datetime.strptime("12.02.2020", "%d.%m.%Y"),
    "confirmed_cases_per_day": [
        0,0,0,0,0,0,0,0,0,0,1,12,3,2,9,23,43,20,36,43,75,148,183,176,134,92,341,579,734,971,1405,1284,939,2006,3010,3505,3963,4017,3250,2285,3644,4771,5577,5790,6032,4733,3078,4129,5969,6164,6397,5943,4028
    ],
    "deaths_per_day": [
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,1,2,4,0,5,3,6,9,12,15,10,26,31,41,34,80,57,53,71,81,97,123,143,113,57,109,122,121,74,41,26
    ],
    "dayToStartLeastSquares": 0,
    "noSymptoms": 0.7,
    "I0": 0,  # Guess - the 17 were all in the resitant category at this point ( or diagnosed)
    "D0": 0,
    "H0": 0,
    "T0": 0,
    "daysToModel": 60,
    "lockdown": 30,
    "length_of_lockdown": 7,
    # Note that the contacts are simulated as if each contact were with a different person.
    # Doing this properly could be done by generating an exposure matrix of people vs number of contacts,
    # e. g. 2 people living in the same household with with a large number of contacts per day,
    # N1 friends or colleagues with a medium number of contacts per day,
    # N2 random people with very few contacts per day.
    # Problem is that the distribution is unknown - and more to the point, it will differ dramatically for
    # people like nurses or doctors or teachers from a pensioner living by himself.
    "numPeopleInfectiousContactPerDay_0": 1.1, # Number of contacts each person is in contact with close enough to infect them on average per day before begin lockdown.
    "numPeopleInfectiousContactPerDay_1": 0.05, # Number of contacts each person is in contact with close enough to infect them on average per day before end lockdown
    "numPeopleInfectiousContactPerDay_2": 0.1, # Number of contacts each person is in contact with close enough to infect them on average per day after end lockdown
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

if len(dataset["confirmed_cases_per_day"]) != len(dataset["deaths_per_day"]):
    print(str(len(dataset["confirmed_cases_per_day"])) + '=len(dataset["confirmed_cases_per_day"]) != len(dataset["deaths_per_day"])=' + str(
        len(dataset["deaths_per_day"])))
    exit(1)

#for i in range(0, len(dataset["confirmed_cases"])):
#    dataset["confirmed_cases"][i] = dataset["confirmed_cases"][i] - dataset["R0"]
#dataset["D0"] = dataset["confirmed_cases"][0]  # must be true for consistency
#dataset["T0"] = dataset["deaths"][0]  # must be true for consistency

logPlot = True

population = int(dataset["population"])

startDate = dataset["start_date"]
daysToModel = dataset["daysToModel"]  # total days to model
E0 = dataset["E0"]  # exposed at initial time step
I0 = dataset["I0"]
D0 = dataset["D0"]
H0 = dataset["H0"]
R0 = dataset["R0"]
T0 = dataset["T0"]
RealND = np.asarray(dataset["confirmed_cases_per_day"])
RealNT = np.asarray(dataset["deaths_per_day"])
daysOfData = len(RealND)
RealX = np.arange(daysOfData)
#D_to_T = RealT[-1] / np.sum(np.asarray(RealD[0:int(-timeDiagnosedToDeath / 2)]))
#D_to_R = 1.0 / 15.0
#I_to_R = 0.0

# Parameters set by external data
noSymptoms = dataset[
    "noSymptoms"]  # https://www.reddit.com/r/COVID19/comments/ffzqzl/estimating_the_asymptomatic_proportion_of_2019/
intensiveUnits = dataset["intensiveUnits"]  # ICU units available
daysBeginLockdown = dataset["lockdown"]  # days before lockdown measures (there probably should be several of those)
daysEndLockdown = daysBeginLockdown + dataset[
    "length_of_lockdown"]  # days before lockdown measures are relaxed (there probably should be several of those)
#beta0 = dataset["beta0"]  # The parameter controlling how often a susceptible-infected contact results in a new infection.
#beta1 = dataset["beta1"]  # beta0 is used during days0 phase, beta1 after days0
#Beta2 = dataset["beta2"]
numPeopleInfectiousContactPerDay_0 = dataset["numPeopleInfectiousContactPerDay_0"]
numPeopleInfectiousContactPerDay_1 = dataset["numPeopleInfectiousContactPerDay_1"]
numPeopleInfectiousContactPerDay_2 = dataset["numPeopleInfectiousContactPerDay_2"]

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
    ('T', np.int),
    ('nE', np.int),
    ('nI', np.int),
    ('nD', np.int),
    ('nH', np.int),
    ('nT', np.int)
])

type_fittedparamblock = np.dtype([
    ('daySocialBehaviourChange', np.int),
    ('infectiousToDiagnosedMean', np.float),
    ('infectiousToDiagnosedSigma', np.float),
    ('numPeopleInfectiousContactPerDay', np.float),
    ('infectiousPeriodValues', np.float, (20,)),
    ('infectiousPeriodProbabilities', np.float, (20,))
])
type_fittedparameters = np.dtype([
    ('E0', np.int),
    ('I0', np.int),
    ('paramBlockArray', type_fittedparamblock, (maxNumSocialBehaviourChanges,))
])

RG = np.random.default_rng()

# https://github.com/HopkinsIDD/ncov_incubation (2020-04-01)
# Calculated in IncubationDiagnosedPeriods.ods
incubationPeriodValues = np.array([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20])
incubationPeriodProbabilities = np.array([0.0001,0.0136,0.0936,0.1818,0.2011,0.1688,0.1225,0.0819,0.0524,0.0326,0.0201,0.0123,0.0075,0.0046,0.0028,0.0018,0.0011,0.0007,0.0004,0.0003])

# https://github.com/HopkinsIDD/ncov_incubation (2020-04-01)
# Calculated in IncubationDiagnosedPeriods.ods
#infectiousPeriodValues = np.array([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20])
#infectiousPeriodProbabilities = np.array([0.5759,0.1430,0.0835,0.0547,0.0378,0.0270,0.0197,0.0145,0.0109,0.0082,0.0062,0.0047,0.0036,0.0028,0.0021,0.0017,0.0013,0.0010,0.0008,0.0006])

infectiousNoSymptomsPeriodValues = np.array([0,1,2,3,4,5,6,7])
infectiousNoSymptomsPeriodProbabilities = np.array([0.3,0.3,0.15,0.10,0.06,0.04,0.03,0.02])

# The model is very, very sensitive to this number....
daysInfectiousBeforeSymptoms = 3

probabilityHospital = 0.2
symptomsToHospitalPeriodValues = np.array([          2,  3,  4,  5,   6,   7,   8,   9,  10,   11,   12,   13,   14])
symptomsToHospitalPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])
probabilityDeadAfterHospital = 0.1
symptomsToDeadPeriodValues = np.array([          8,  9, 10, 11, 12, 13,  14,  15,  16,  17,  18,   19,   20])
symptomsToDeadPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])
symptomsToRecoveredPeriodValues = np.array([         20, 21, 22, 23,   24,  25,  26,  27,  28,   29,   30,   31,   32])
symptomsToRecoveredPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])

symptomsToRecoveredPeriodValues = np.array([         7,  8,   9,  10,  11,  12,  13,  14])
symptomsToRecoveredPeriodProbabilities = np.array([0.4,0.35,0.12,0.06,0.03,0.02,0.01,0.01])

def createExposed(day_exposed, paramBlock):
    day_with_symptoms = day_exposed+RG.choice(incubationPeriodValues, p=incubationPeriodProbabilities)
    day_infectious = day_with_symptoms-daysInfectiousBeforeSymptoms
    if RG.random()>=probabilityNoSymptoms:
        mean = paramBlock['infectiousToDiagnosedMean']
        sigma = paramBlock['infectiousToDiagnosedSigma']
        i_to_d = RG.lognormal(mean, sigma)
        day_diagnosed = day_with_symptoms+i_to_d
        if RG.random()< probabilityHospital:
            day_hospitalized = day_with_symptoms+RG.choice(symptomsToHospitalPeriodValues, p=symptomsToHospitalPeriodProbabilities)
            if RG.random()< probabilityDeadAfterHospital:
                day_died = day_with_symptoms+RG.choice(symptomsToDeadPeriodValues, p=symptomsToDeadPeriodProbabilities)
                day_recovered = np.iinfo(np.int).max
            else:
                day_recovered = day_with_symptoms+RG.choice(symptomsToRecoveredPeriodValues, p=symptomsToRecoveredPeriodProbabilities)
                day_died = np.iinfo(np.int).max
            if day_hospitalized>=min(day_recovered,day_died):
                day_hospitalized = np.iinfo(np.int).max
        else:
            day_hospitalized = np.iinfo(np.int).max
            day_recovered = day_with_symptoms+RG.choice(symptomsToRecoveredPeriodValues, p=symptomsToRecoveredPeriodProbabilities)
            day_died = np.iinfo(np.int).max
    else:
        day_diagnosed = np.iinfo(np.int).max
        day_hospitalized = np.iinfo(np.int).max
        day_died = np.iinfo(np.int).max
        day_recovered = day_infectious + RG.choice(infectiousNoSymptomsPeriodValues, p=infectiousNoSymptomsPeriodProbabilities)
    a = np.array([(day_exposed, day_infectious, day_diagnosed, day_hospitalized, day_recovered, day_died)], type_individual)
    return a[0]

def createNewlyExposed(day_exposed, N, paramBlock):
    newlyExposed = np.empty(N, type_individual)
    for i in range(0, N):
        e = createExposed(day_exposed, paramBlock)
        newlyExposed[i] = e
    return newlyExposed

def advanceDay(day, statsperday, pop, paramBlock):
    numPeopleInfectiousContactPerDay = paramBlock["numPeopleInfectiousContactPerDay"]

    # One infected person will generate beta * S / population new
    # exposed people in a time step.
    pS = statsperday[day-1]['S']
    pE = statsperday[day-1]['E']
    pI = statsperday[day-1]['I']
    pD = statsperday[day-1]['D']
    pH = statsperday[day-1]['H']
    pR = statsperday[day-1]['R']
    pT = statsperday[day-1]['T']

    popR = pop['day_recovered']<=day
    popT = pop['day_died']<=day
    npop = pop[np.logical_not(np.logical_or(popR, popT))]
    dR = np.count_nonzero(popR)
    dT = np.count_nonzero(popT)
    R = pR + dR
    T = pT + dT

    prob = pS / population
    numnewexposed = RG.binomial(pI * numPeopleInfectiousContactPerDay, prob)

    #createExposedUFunc = np.frompyfunc(lambda n: createExposed(day), 1, 1)
    #newexposed = np.fromfunction(createExposedUFunc, (numnewexposed,))
    newexposed = createNewlyExposed(day, numnewexposed, paramBlock)
    npop = np.append(npop, newexposed)

    nE = np.count_nonzero(npop['day_exposed']==day)
    I = np.count_nonzero(npop['day_infectious']<=day)
    nI = np.count_nonzero(npop['day_infectious']==day)
    D = np.count_nonzero(npop['day_diagnosed']<=day)
    nD = np.count_nonzero(npop['day_diagnosed']==day)
    H = np.count_nonzero(npop['day_hospitalized']<=day)
    nH = np.count_nonzero(npop['day_hospitalized']==day)
    I = I - D
    D = D - H

    statsperday[day]['S'] = pS - numnewexposed
    statsperday[day]['E'] = pE + numnewexposed - (I+D+H+dR+dT - pI-pD-pH)
    statsperday[day]['I'] = I
    statsperday[day]['D'] = D
    statsperday[day]['H'] = H
    statsperday[day]['R'] = R
    statsperday[day]['T'] = T
    statsperday[day]['nE'] = nE
    statsperday[day]['nI'] = nI
    statsperday[day]['nD'] = nD  # we need all *new* diagnosed, without subtracting the ones going elsewhere - that is what is generally counted
    statsperday[day]['nH'] = nH
    statsperday[day]['nT'] = dT

    return npop

#exposed = createExposed(0)
#pop = np.full(10, exposed, type_individual)
#createExposed0UFunc = np.frompyfunc(lambda n: createExposed(0), 1, 1)
#pop = np.fromfunction(createExposed0UFunc, [E0])

def calcStatsPerDay(days, xdata):
    E0 = int(xdata['E0'])
    I0 = int(xdata['I0'])

    paramBlockArray = xdata['paramBlockArray']
    paramBlockIndex = 0

    pop = createNewlyExposed(0, E0, paramBlockArray[0])

    statsperday = np.zeros(days, type_statsperday)
    statsperday[0]['S'] = population - E0 - I0 - D0 - H0 - R0 - T0
    statsperday[0]['E'] = E0
    statsperday[0]['I'] = I0
    statsperday[0]['D'] = D0
    statsperday[0]['H'] = H0
    statsperday[0]['R'] = R0
    statsperday[0]['T'] = T0
    statsperday[0]['nI'] = 0
    statsperday[0]['nD'] = 0
    statsperday[0]['nH'] = 0
    statsperday[0]['nT'] = 0

    for day in range(1, days):
        while paramBlockIndex<maxNumSocialBehaviourChanges-1 and paramBlockArray[paramBlockIndex+1]['daySocialBehaviourChange']<day:
            paramBlockIndex += 1
        paramBlock = paramBlockArray[paramBlockIndex]
        pop = advanceDay(day, statsperday, pop, paramBlock)
        print(day, paramBlockIndex, statsperday[day])

    return statsperday

def solveForLeastSq(xdata):
    statsperday = calcStatsPerDay(daysOfData, xdata)

    dD = statsperday['nD']
    dT = statsperday['nT']

    o = 0.5*np.nansum(np.square((np.log(dD+1) - np.log(RealND[0:]+1)))) + \
        0.5*np.nansum(np.square(np.log(dT+1) - np.log(RealNT[0:]+1)))
    print(o,"  for: ",xdata)
    return o

def calculateAll(startValues):
    optimizeValues = startValues

    if False:
        print("Starting values: E0: %.3g" % E0,"I0: %.3g" % I0, "NumInf0: %.3g" % numPeopleInfectiousContactPerDay_0, "NumInf1: %.3g" % numPeopleInfectiousContactPerDay_1)
        r = scipy.optimize.least_squares(solveForLeastSq, optimizeValues,
                                bounds=(np.asarray([     1,     0,   0.5,  0.01]),
                                        np.asarray([np.inf,np.inf,   1.5,  0.5]))
                                 )
        E0, I0, numPeopleInfectiousContactPerDay_0, numPeopleInfectiousContactPerDay_1 = r['x']
        print("Optimized values: E0: %.3g" % E0,"I0: %.3g" % I0, "NumInf0: %.3g" % numPeopleInfectiousContactPerDay_0, "NumInf1: %.3g" % numPeopleInfectiousContactPerDay_1)
    else:
        allv = []
        for e in range(100, 151, 25):
            for i in range(0, 51, 25):
                for numinf_0 in np.linspace(0.5, 1.5, 5):
                    for numinf_1 in np.linspace(0.50, 0.51, 1):
                        allv.append([e, i, numinf_0, numinf_1])
        with multiprocessing.Pool(16) as p:
            w = p.map(solveForLeastSq, allv)

def plot(v, numdays):
    # Plot
    statsperday = calcStatsPerDay(numdays, v)
    fig = plt.figure(dpi=75, figsize=(20,16))
    ax = fig.add_subplot(111)
    if logPlot:
        ax.set_yscale("log", nonposy='clip')


    X = np.arange(0, numdays)

    days = matplotlib.dates.drange(startDate, startDate + datetime.timedelta(days=numdays), datetime.timedelta(days=1))

    E = statsperday['E']
    I = statsperday['I']
    D = statsperday['D']
    H = statsperday['H']
    R = statsperday['R']
    T = statsperday['T']
    nE = statsperday['nE']
    nI = statsperday['nI']
    nD = statsperday['nD']
    nH = statsperday['nH']
    nT = statsperday['nT']

    ax.plot(days, nE, 'y', alpha=0.5, lw=1, label='New exposed', ls='--')
    ax.plot(days, nI, 'b', alpha=0.5, lw=1, label='New infectious')
    ax.plot(days, nD, 'g', alpha=0.5, lw=1, label='New diagnosed and isolated')
    ax.plot(days, nH, 'm', alpha=0.5, lw=1, label='New hospitalized')
    ax.plot(days[:min(daysOfData, numdays)], RealND[:min(daysOfData, numdays)], 'r', alpha=0.5, lw=1, label='Confirmed cases per day')
    #ax.plot(X, R, 'y', alpha=0.5, lw=1, label='Recovered with immunity')
    ax.plot(days, nT, 'k', alpha=0.5, lw=1, label='New deaths')
    ax.plot(days[:min(daysOfData, numdays)], RealNT[0:min(daysOfData, numdays)], 'c', alpha=0.5, lw=1, label='Confirmed deaths per day')

    ax.set_xlabel('Time /days')
    ax.set_ylabel('Number (1000s)')
    ax.set_ylim(bottom=1.0)
    ax.set_xlim(left=days[0])
    formatter = matplotlib.dates.DateFormatter("%m-%d")
    ax.xaxis.set_major_formatter(formatter)
    ax.xaxis.set_minor_locator(matplotlib.dates.DayLocator(interval=1))
    ax.xaxis.set_major_locator(matplotlib.dates.WeekdayLocator(byweekday=1,interval=1))

    ax.grid(linestyle=':', which='minor', axis='both')  #b=True, which='major', c='w', lw=2, ls='-')
    ax.grid(linestyle='--', which='major', axis='both')  #b=True, which='major', c='w', lw=2, ls='-')
    legend = ax.legend(title='COVID-19 SEIR model'+
                       ' %dk' % (population / 1000) + ' (beta)')
    legend.get_frame().set_alpha(0.5)
    for spine in ('top', 'right', 'bottom', 'left'):
        ax.spines[spine].set_visible(False)
    cursor = matplotlib.widgets.Cursor(ax, color='black', linewidth=1 )
    plt.show()

if __name__ == '__main__':
    #v = [E0, I0, numPeopleInfectiousContactPerDay_0, numPeopleInfectiousContactPerDay_1]
    #calculateAll(v)
    v =  np.empty((1,), type_fittedparameters)[0]
    v['E0'] = 100
    v['I0'] = 50
    v['paramBlockArray'][0]['daySocialBehaviourChange'] = 0
    v['paramBlockArray'][0]['infectiousToDiagnosedMean'] = np.log(8)
    v['paramBlockArray'][0]['infectiousToDiagnosedSigma'] = np.log(1.5)
    v['paramBlockArray'][0]['numPeopleInfectiousContactPerDay'] = 0.95
    v['paramBlockArray'][1]['daySocialBehaviourChange'] = 25
    v['paramBlockArray'][1]['infectiousToDiagnosedMean'] = np.log(8)
    v['paramBlockArray'][1]['infectiousToDiagnosedSigma'] = np.log(1.5)
    v['paramBlockArray'][1]['numPeopleInfectiousContactPerDay'] = 0.3
    v['paramBlockArray'][2]['daySocialBehaviourChange'] = 40
    v['paramBlockArray'][2]['infectiousToDiagnosedMean'] = np.log(8)
    v['paramBlockArray'][2]['infectiousToDiagnosedSigma'] = np.log(1.5)
    v['paramBlockArray'][2]['numPeopleInfectiousContactPerDay'] = 0.01
    v['paramBlockArray'][3]['daySocialBehaviourChange'] = 1000
    v['paramBlockArray'][3]['infectiousToDiagnosedMean'] = np.log(8)
    v['paramBlockArray'][3]['infectiousToDiagnosedSigma'] = np.log(1.5)
    v['paramBlockArray'][3]['numPeopleInfectiousContactPerDay'] = 0.4

    plot(v, 70)
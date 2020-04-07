import math
import numpy as np
import scipy.integrate
import scipy.optimize
import matplotlib.pyplot as plt
import matplotlib.widgets  # Cursor
import datetime
import multiprocessing

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
    "start_date": datetime.datetime.strptime("13.02.2020", "%d.%m.%Y"),
    "confirmed_cases_per_day": [
        0,0,0,0,0,0,0,0,0,0,1,12,3,2,9,23,43,20,36,43,75,148,183,176,134,92,341,579,734,971,1405,1284,939,2006,3011,3496,3961,4013,3247,2286,3638,4762,5568,5789,6022,4725,3074,4118,5940,6046,6228
    ],
    "deaths_per_day": [
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,1,2,4,0,5,3,5,9,12,14,10,25,28,39,32,80,51,48,67,75,90,112,122,96,47,88,99,83,52
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

daysToModel = dataset["daysToModel"]  # total days to model
E0 = dataset["E0"]  # exposed at initial time step
I0 = dataset["I0"]
D0 = dataset["D0"]
H0 = dataset["H0"]
R0 = dataset["R0"]
T0 = dataset["T0"]
RealDpD = np.asarray(dataset["confirmed_cases_per_day"])
RealTpD = np.asarray(dataset["deaths_per_day"])
daysOfData = len(RealDpD)
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
    ('dI', np.int),
    ('dD', np.int),
    ('dT', np.int)
])

type_fittedparamblock = np.dtype([
    ('daySocialBehaviourChange', np.int),
    ('i_to_d_mean', np.float),
    ('i_to_d_sigma', np.float),
    ('numPeopleInfectiousContactPerDay', np.int),
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
diagToHospitalPeriodValues = np.array([          2,  3,  4,  5,   6,   7,   8,   9,  10,   11,   12,   13,   14])
diagToHospitalPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])
probabilityDeadAfterHospital = 0.1
infectionsToDeadPeriodValues = np.array([         10, 11, 12, 13,  14,  15,  16,  17,  18,   19,   20,   21,   22])
infectionsToDeadPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])
infectionsToRecoveredPeriodValues = np.array([         20, 21, 22, 23,   24,  25,  26,  27,  28,   29,   30,   31,   32])
infectionsToRecoveredPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])

diagToRecoveredPeriodValues = np.array([         7,  8,   9,  10,  11,  12,  13,  14])
diagToRecoveredPeriodProbabilities = np.array([0.4,0.35,0.12,0.06,0.03,0.02,0.01,0.01])

def createExposed(day_exposed, paramBlock):
    day_with_symptoms = day_exposed+RG.choice(incubationPeriodValues, p=incubationPeriodProbabilities)
    day_infectious = day_with_symptoms-daysInfectiousBeforeSymptoms
    if RG.random()>=probabilityNoSymptoms:
        mean = paramBlock['i_to_d_mean']
        sigma = paramBlock['i_to_d_sigma']
        i_to_d = RG.lognormal(mean, sigma)
        day_diagnosed = day_with_symptoms+i_to_d
        if RG.random()< probabilityHospital:
            day_hospitalized = day_diagnosed+RG.choice(diagToHospitalPeriodValues, p=diagToHospitalPeriodProbabilities)
            if RG.random()< probabilityDeadAfterHospital:
                day_died = day_infectious+RG.choice(infectionsToDeadPeriodValues, p=infectionsToDeadPeriodProbabilities)
                day_recovered = daysToModel * 1000
            else:
                day_recovered = day_infectious+RG.choice(infectionsToRecoveredPeriodValues, p=infectionsToRecoveredPeriodProbabilities)
                day_died = daysToModel * 1000
            if day_hospitalized<day_recovered or day_hospitalized<day_died:
                day_hospitalized = daysToModel * 1000
        else:
            day_hospitalized = daysToModel * 1000
            day_recovered = day_diagnosed+RG.choice(diagToRecoveredPeriodValues, p=diagToRecoveredPeriodProbabilities)
            day_died = daysToModel * 1000
    else:
        day_diagnosed = daysToModel * 1000
        day_hospitalized = daysToModel * 1000
        day_died = daysToModel * 1000
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

    popR = np.logical_and(pop['day_recovered']<=day,pop['day_recovered']>=0)
    popT = np.logical_and(pop['day_died']<=day,pop['day_died']>=0)
    npop = pop[np.logical_not(np.logical_or(popR, popT))]
    dR = np.count_nonzero(popR)
    dT = np.count_nonzero(popT)
    R = pR + dR
    T = pT + dT

    I = np.count_nonzero(npop['day_infectious']<=day)
    D = np.count_nonzero(npop['day_diagnosed']<=day)
    H = np.count_nonzero(npop['day_hospitalized']<=day)
    I = I - D
    D = D - H

    prob = pS / population
    numnewexposed = RG.binomial(I * numPeopleInfectiousContactPerDay, prob)

    #createExposedUFunc = np.frompyfunc(lambda n: createExposed(day), 1, 1)
    #newexposed = np.fromfunction(createExposedUFunc, (numnewexposed,))
    newexposed = createNewlyExposed(day, numnewexposed, paramBlock)

    npop = np.append(npop, newexposed)

    statsperday[day]['S'] = pS - numnewexposed
    statsperday[day]['E'] = pE + numnewexposed - (I+D+H+dR+dT - pI-pD-pH)
    statsperday[day]['I'] = I
    statsperday[day]['D'] = D
    statsperday[day]['H'] = H
    statsperday[day]['R'] = R
    statsperday[day]['T'] = T
    statsperday[day]['dI'] = I - pI
    statsperday[day]['dD'] = D - pD
    statsperday[day]['dT'] = dT

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
    statsperday[0]['dI'] = 0
    statsperday[0]['dD'] = 0
    statsperday[0]['dT'] = 0

    for day in range(1, days):
        while paramBlockIndex<maxNumSocialBehaviourChanges-1 and paramBlockArray[paramBlockIndex+1]['daySocialBehaviourChange']<day:
            paramBlockIndex += 1
        paramBlock = paramBlockArray[paramBlockIndex]
        pop = advanceDay(day, statsperday, pop, paramBlock)
        print(paramBlockIndex, statsperday[day])

    return statsperday

def solveForLeastSq(xdata):
    statsperday = calcStatsPerDay(daysOfData, xdata)

    dD = statsperday['dD']
    dT = statsperday['dT']

    o = 0.5*np.nansum(np.square((np.log(dD+1) - np.log(RealDpD[0:]+1)))) + \
        0.5*np.nansum(np.square(np.log(dT+1) - np.log(RealTpD[0:]+1)))
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

def plot(v):
    # Plot
    statsperday = calcStatsPerDay(daysToModel, v)
    fig = plt.figure(dpi=75, figsize=(20,16))
    ax = fig.add_subplot(111)
    if logPlot:
        ax.set_yscale("log", nonposy='clip')


    X = np.arange(0, daysToModel)
    I = statsperday['I']
    D = statsperday['D']
    H = statsperday['H']
    R = statsperday['R']
    T = statsperday['T']
    dI = statsperday['dI']
    dD = statsperday['dD']
    dT = statsperday['dT']

    ax.plot(X, dI, 'b', alpha=0.5, lw=1, label='Infectious')
    ax.plot(X, dD, 'g', alpha=0.5, lw=1, label='Diagnosed and isolated')
    #ax.plot(X, np.cumsum(D), 'm', alpha=0.5, lw=1, label='Cumulative diagnosed and isolated')
    ax.plot(RealX[0:], RealDpD[0:], 'r', alpha=0.5, lw=1, label='Confirmed cases')
    #ax.plot(X, R, 'y', alpha=0.5, lw=1, label='Recovered with immunity')
    ax.plot(X, dT, 'k', alpha=0.5, lw=1, label='Deaths')
    ax.plot(RealX[0:], RealTpD[0:], 'c', alpha=0.5, lw=1, label='Confirmed deaths')

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

if __name__ == '__main__':
    #v = [E0, I0, numPeopleInfectiousContactPerDay_0, numPeopleInfectiousContactPerDay_1]
    #calculateAll(v)
    v =  np.empty((1,), type_fittedparameters)[0]
    v['E0'] = 10
    v['I0'] = 0
    v['paramBlockArray'][0]['daySocialBehaviourChange'] = 0
    v['paramBlockArray'][0]['i_to_d_mean'] = 1.6
    v['paramBlockArray'][0]['i_to_d_sigma'] = 0.4
    v['paramBlockArray'][0]['numPeopleInfectiousContactPerDay'] = 1.0
    v['paramBlockArray'][1]['daySocialBehaviourChange'] = 30
    v['paramBlockArray'][1]['i_to_d_mean'] = 1.6
    v['paramBlockArray'][1]['i_to_d_sigma'] = 0.4
    v['paramBlockArray'][1]['numPeopleInfectiousContactPerDay'] = 0.6
    v['paramBlockArray'][2]['daySocialBehaviourChange'] = 37
    v['paramBlockArray'][2]['i_to_d_mean'] = 1.6
    v['paramBlockArray'][2]['i_to_d_sigma'] = 0.4
    v['paramBlockArray'][2]['numPeopleInfectiousContactPerDay'] = 0.3
    v['paramBlockArray'][3]['daySocialBehaviourChange'] = 1000
    v['paramBlockArray'][3]['i_to_d_mean'] = 1.6
    v['paramBlockArray'][3]['i_to_d_sigma'] = 0.4
    v['paramBlockArray'][3]['numPeopleInfectiousContactPerDay'] = 1.0

    plot(v)
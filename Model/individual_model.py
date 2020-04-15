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

RG = np.random.default_rng()

# NEXT:
# Heinsberg study gives letality rate of 0.4% (dead/infected). This suggests people without symptoms are relatively numerous. Check if their progression needs better modelling - pay more attention to the time infectious people need to notice they are infectious, cause that is what a contact tracing app can fix.
# Why is there a change on the 9th of march in the current model? Try to model date changes more in line with actual events, maybe allow for an adjustment period, phasing in infection rate changes.
# How to get the rate infectious/hospitalized in a sensible fashion? That presumably will not be fixed but different from country to country, but still probably about the same for western countries?
# Try to accelerate the generation of exposed (but first check if that is relevant).
# Get the numbers for Austria and run it with that. Similar to Germany, should allow to figure out the coefficient for the lock-down period.
# Then run Italy again, followed by UK
# Try to compare hospital numbers with real stats.
# Compare with healthdata.org

type_statsperday = np.dtype([
    ('S', np.int),
    ('E', np.int),
    ('I', np.int),
    ('D', np.int), # Isolated
    ('H', np.int),
    ('R', np.int),
    ('T', np.int),
    ('nE', np.int),
    ('nI', np.int),
    ('nD', np.int),
    ('nH', np.int),
    ('nT', np.int)
])

type_individual = np.dtype([
    ('day_exposed', np.int),
    ('day_infectious', np.int),
    ('day_diagnosed', np.int),
    ('day_hospitalized', np.int),
    ('day_recovered', np.int),
    ('day_died', np.int)
])

fixed_common = {
    "DaySymptoms": lambda num: RG.lognormal(np.log(5), np.log(1.5), (num,)),
    "DayInfBefSymptoms": lambda num: np.full(num, 2.5),
    "DaysSymptomsToIsolation": lambda num, mean, sigma: RG.lognormal(np.log(mean),np.log(sigma),(num,)),
    "DaysSymptomsToR": lambda num: RG.lognormal(np.log(5), np.log(1.5)),
    "FractionDiagHosp": 0.2,
    "DaysSymptomsToH": lambda num: RG.gamma(5.5, 1.0, (num,)),
    "DaysHToR": lambda num: RG.lognormal(18, 2, (num,)),
    "DaysSymptomsToRViaIso": lambda num:  RG.lognormal(np.log(7), np.log(1.3)),
    "IsDiagnosed": lambda num, p: RG.random(num)<=p,
    "IsHospitalized": lambda num, p: RG.random(num) <= p,
    "IsDeceased": lambda num, p: RG.random(num) <= p
}

fixed_germany = {
    "N": 81E6,
    "D0": 1,
    "H0": 0,
    "R0": 16,
    "T0": 0,
    "FractionContractTracing": 0.0,
    "DayIsoDirect": lambda num: RG.lognormal(np.log(2), np.log(1.5), (num,)),
    "DaysSymptomsToD": lambda num: RG.lognormal(np.log(25), np.log(1.5), (num,)),
    "DaysTestingChanged": [],
    "DaysSocialBehaviourChanged": [25, 40],
    "FractionDeceased": 0.11,

    # Date when Health Minister said "Infection chains are no longer traceable"
    # 12th of March: Merkel recommends social distancing
    # 14th-16th of March (Day 26-28): Closing of schools
    # 22nd of March (Day 34): General restrictions to meet in public (the week before various restrictions depending ons the individual Länder)
    "start_date": datetime.datetime.strptime("12.02.2020", "%d.%m.%Y"),
    "confirmed_cases_per_day": [
        2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 4, 26, 10, 54, 18, 28, 39, 66, 138, 284, 163, 55, 237, 157, 271,
        802, 693, 733, 1043, 1174, 1144, 1042, 5940, 4049, 3276, 3311, 4438, 2342, 4954, 5780, 6294, 3965, 4751, 4615,
        5453, 6156, 6174, 6082, 5936, 3677, 3834, 4003, 4974, 5323, 4133
    ],
    "deaths_per_day": [
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 1, 2, 0, 3, 4, 1, 0, 0,
        30, 2, 22, 27, 32, 23, 49, 55, 72, 64, 66, 128, 149, 140, 145, 141, 184, 92, 173, 254, 246, 266, 171
    ],
}

fitted_germany = {
    "E0": 100,
    "I0": 50,
    "FractionInfDiagnosed": [ 0.2, 0.2, 0.2 ],
    "DaysSymptomsToIsolation_Mean": [ 8, 8, 8 ],
    "DaysSymptomsToIsolation_Sigma": [ 1.5, 1.5, 1.5 ],
    "InfectiousContactsPerDay": [ 0.87, 0.22, 0.05 ]
}

class Dataset:
    def __init__(self, common, fixed, fitted):
        self.common = common
        self.fixed = fixed
        self.fitted = fitted

    @classmethod
    def datasetForPeriod(cls, common, fixed, fitted):
        assert len(fixed["confirmed_cases_per_day"]) == len(fixed["deaths_per_day"])
        assert len(fixed["DaysSocialBehaviourChanged"]) + 1 == len(fitted["FractionInfDiagnosed"])
        assert len(fixed["DaysSocialBehaviourChanged"]) + 1 == len(fitted["DaysSymptomsToIsolation_Mean"])
        assert len(fixed["DaysSocialBehaviourChanged"]) + 1 == len(fitted["DaysSymptomsToIsolation_Sigma"])
        assert len(fixed["DaysSocialBehaviourChanged"]) + 1 == len(fitted["InfectiousContactsPerDay"])
        return cls(common, fixed, fitted)

    @classmethod
    def datasetForDay(cls, dataset, day):
        thresholdIndex = 0
        thresholds = dataset["DaysSocialBehaviourChanged"]
        while thresholdIndex<len(thresholds):
            if day<thresholds[thresholdIndex]:
                break
            thresholdIndex += 1
        fittedForDay = dict.copy(dataset.fitted)
        fittedForDay["FractionInfDiagnosed"] = dataset.fitted["FractionInfDiagnosed"][thresholdIndex]
        fittedForDay["DaysSymptomsToIsolation_Mean"] = dataset.fitted["DaysSymptomsToIsolation_Mean"][thresholdIndex]
        fittedForDay["DaysSymptomsToIsolation_Sigma"] = dataset.fitted["DaysSymptomsToIsolation_Sigma"][thresholdIndex]
        fittedForDay["InfectiousContactsPerDay"] = dataset.fitted["InfectiousContactsPerDay"][thresholdIndex]
        return cls(dataset.common, dataset.fixed, fittedForDay)

    def __getitem__(self, key):
        try:
            return self.fitted[key]
        except:
            try:
                return self.fixed[key]
            except:
                return self.common[key]

    def __contains__(self, item):
        return item in self.fitted or item in self.fixed or item in self.common

    def forDay(self, day):
        return Dataset.datasetForDay(self, day)

    def startDate(self):
        return self.fixed["start_date"]

    def daysOfData(self):
        return len(self.fixed["deaths_per_day"])

# population = int(dataset["population"])
#
# startDate = dataset["start_date"]
# daysToModel = dataset["daysToModel"]  # total days to model
# E0 = dataset["E0"]  # exposed at initial time step
# I0 = dataset["I0"]
# D0 = dataset["D0"]
# H0 = dataset["H0"]
# R0 = dataset["R0"]
# T0 = dataset["T0"]
# RealND = np.asarray(dataset["confirmed_cases_per_day"])
# RealNT = np.asarray(dataset["deaths_per_day"])
# daysOfData = len(RealND)
# RealX = np.arange(daysOfData)
#D_to_T = RealT[-1] / np.sum(np.asarray(RealD[0:int(-timeDiagnosedToDeath / 2)]))
#D_to_R = 1.0 / 15.0
#I_to_R = 0.0

# Parameters set by external data
#noSymptoms = dataset["noSymptoms"]  # https://www.reddit.com/r/COVID19/comments/ffzqzl/estimating_the_asymptomatic_proportion_of_2019/
#intensiveUnits = dataset["intensiveUnits"]  # ICU units available
#daysBeginLockdown = dataset["lockdown"]  # days before lockdown measures (there probably should be several of those)
#daysEndLockdown = daysBeginLockdown + dataset["length_of_lockdown"]  # days before lockdown measures are relaxed (there probably should be several of those)
#beta0 = dataset["beta0"]  # The parameter controlling how often a susceptible-infected contact results in a new infection.
#beta1 = dataset["beta1"]  # beta0 is used during days0 phase, beta1 after days0
#Beta2 = dataset["beta2"]
#numPeopleInfectiousContactPerDay_0 = dataset["numPeopleInfectiousContactPerDay_0"]
#numPeopleInfectiousContactPerDay_1 = dataset["numPeopleInfectiousContactPerDay_1"]
#numPeopleInfectiousContactPerDay_2 = dataset["numPeopleInfectiousContactPerDay_2"]

# https://github.com/HopkinsIDD/ncov_incubation (2020-04-01)
# Calculated in IncubationDiagnosedPeriods.ods
#incubationPeriodValues = np.array([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20])
#incubationPeriodProbabilities = np.array([0.0001,0.0136,0.0936,0.1818,0.2011,0.1688,0.1225,0.0819,0.0524,0.0326,0.0201,0.0123,0.0075,0.0046,0.0028,0.0018,0.0011,0.0007,0.0004,0.0003])

# https://github.com/HopkinsIDD/ncov_incubation (2020-04-01)
# Calculated in IncubationDiagnosedPeriods.ods
#infectiousPeriodValues = np.array([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20])
#infectiousPeriodProbabilities = np.array([0.5759,0.1430,0.0835,0.0547,0.0378,0.0270,0.0197,0.0145,0.0109,0.0082,0.0062,0.0047,0.0036,0.0028,0.0021,0.0017,0.0013,0.0010,0.0008,0.0006])

#infectiousNoSymptomsPeriodValues = np.array([0,1,2,3,4,5,6,7])
#infectiousNoSymptomsPeriodProbabilities = np.array([0.3,0.3,0.15,0.10,0.06,0.04,0.03,0.02])

# The model is very, very sensitive to this number....
#daysInfectiousBeforeSymptoms = 2

#probabilityHospital = 0.2
#symptomsToHospitalPeriodValues = np.array([          2,  3,  4,  5,   6,   7,   8,   9,  10,   11,   12,   13,   14])
#symptomsToHospitalPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])
#probabilityDeadAfterHospital = 0.1
#symptomsToDeadPeriodValues = np.array([          8,  9, 10, 11, 12, 13,  14,  15,  16,  17,  18,   19,   20])
#symptomsToDeadPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])
#symptomsToRecoveredPeriodValues = np.array([         20, 21, 22, 23,   24,  25,  26,  27,  28,   29,   30,   31,   32])
#symptomsToRecoveredPeriodProbabilities = np.array([0.05,0.1,0.2,0.4,0.12,0.06,0.03,0.02,0.01,0.004,0.003,0.002,0.001])

#symptomsToRecoveredPeriodValues = np.array([         7,  8,   9,  10,  11,  12,  13,  14])
#symptomsToRecoveredPeriodProbabilities = np.array([0.4,0.35,0.12,0.06,0.03,0.02,0.01,0.01])

def createNewlyExposed(day_exposed, N, p):
    maxday = np.iinfo(np.int).max
    day_with_symptoms = day_exposed+p['DaySymptoms'](N)
    day_infectious = day_with_symptoms-p['DayInfBefSymptoms'](N)
    is_diagnosed = p['IsDiagnosed'](N, p['FractionInfDiagnosed'])
    day_diagnosed = np.ma.masked_array(data=day_with_symptoms+p['DaysSymptomsToIsolation'](N, p['DaysSymptomsToIsolation_Mean'], p['DaysSymptomsToIsolation_Sigma']),
                                mask=~is_diagnosed)
    is_hospitalized = np.logical_and(is_diagnosed, p['IsHospitalized'](N, p['FractionDiagHosp']))
    day_hospitalized = np.ma.masked_array(data=day_with_symptoms+p['DaysSymptomsToH'](N),
                                mask=~is_hospitalized)
    is_deceased = p['IsDeceased'](N, p['FractionDeceased'])
    day_deceased = np.ma.masked_array(data=day_with_symptoms+p['DaysSymptomsToD'](N),
                                mask=~np.logical_and(is_hospitalized, is_deceased))
    pick_way_of_recovery = is_diagnosed.astype(int) + is_hospitalized.astype(int)
    duration_of_recovery = [
                            day_with_symptoms+p['DaysSymptomsToR'](N),
                            day_with_symptoms+p['DaysSymptomsToRViaIso'](N),
                            day_with_symptoms+p['DaysHToR'](N)
                        ]
    day_recovered = np.ma.masked_array(
                                data=np.choose(pick_way_of_recovery, duration_of_recovery),
                                mask=np.logical_and(is_hospitalized, is_deceased))
    r = np.rec.fromarrays([
        np.full((N,), day_exposed),
        np.rint(day_infectious),
        np.rint(day_diagnosed.filled(maxday)),
        np.rint(day_hospitalized.filled(maxday)),
        np.rint(day_recovered.filled(maxday)),
        np.rint(day_deceased.filled(maxday))
    ], names='day_exposed,day_infectious,day_diagnosed,day_hospitalized,day_recovered,day_deceased')
    return r

def advanceDay(day, statsperday, pop, paramsForDay):
    numPeopleInfectiousContactPerDay = paramsForDay["InfectiousContactsPerDay"]

    # One infected person will generate beta * S / population new
    # exposed people in a time step.
    N = paramsForDay['N']
    pS = statsperday[day-1]['S']
    pE = statsperday[day-1]['E']
    pI = statsperday[day-1]['I']
    pD = statsperday[day-1]['D']
    pH = statsperday[day-1]['H']
    pR = statsperday[day-1]['R']
    pT = statsperday[day-1]['T']

    popR = pop['day_recovered']<=day
    popT = pop['day_deceased']<=day
    npop = pop[np.logical_not(np.logical_or(popR, popT))]
    dR = np.count_nonzero(popR)
    dT = np.count_nonzero(popT)
    R = pR + dR
    T = pT + dT

    prob = pS / N
    numnewexposed = RG.binomial(pI * numPeopleInfectiousContactPerDay, prob)

    #createExposedUFunc = np.frompyfunc(lambda n: createExposed(day), 1, 1)
    #newexposed = np.fromfunction(createExposedUFunc, (numnewexposed,))
    newexposed = createNewlyExposed(day, numnewexposed, paramsForDay)
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

def calcStatsPerDay(days, d):
    E0 = int(d['E0'])
    I0 = int(d['I0'])
    D0 = int(d['D0'])
    H0 = int(d['H0'])
    R0 = int(d['R0'])
    T0 = int(d['T0'])
    N = int(d['N'])

    paramsForDay = d.forDay(0)
    pop = createNewlyExposed(0, E0, paramsForDay)

    statsperday = np.zeros(days, type_statsperday)
    statsperday[0]['S'] = N - E0 - I0 - D0 - H0 - R0 - T0
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
        paramsForDay = d.forDay(day)
        pop = advanceDay(day, statsperday, pop, paramsForDay)
        print(day, statsperday[day])

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

def plot(d, numdays):
    # Plot
    logPlot = True

    startDate = d.startDate()
    daysOfData = d.daysOfData()
    N = int(d['N'])
    RealND = np.asarray(d["confirmed_cases_per_day"])
    RealNT = np.asarray(d["deaths_per_day"])

    statsperday = calcStatsPerDay(numdays, d)
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
                       ' %dk' % (N / 1000) + ' (beta)')
    legend.get_frame().set_alpha(0.5)
    for spine in ('top', 'right', 'bottom', 'left'):
        ax.spines[spine].set_visible(False)
    cursor = matplotlib.widgets.Cursor(ax, color='black', linewidth=1 )
    plt.show()

if __name__ == '__main__':
    d = Dataset.datasetForPeriod(fixed_common, fixed_germany, fitted_germany)

    plot(d, 70)




fixed_italy = {
    # Start date determined by first death - 14 days
    #"start_date": datetime.datetime.strptime("07.02.2020", "%d.%m.%Y"),
    #"confirmed_cases": [
    #    3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 20, 62, 155, 229, 322, 453, 655, 888, 1128, 1694, 2036, 2502, 3089,
    #    3858, 4636, 5883, 7375, 9172, 10149, 12462, 12462, 17660, 21157, 24747, 27980, 31506, 35713, 41035, 47021,
    #    53578, 59138, 63927, 69176, 74386
    #],
    #"deaths": [
    #    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 7, 10, 12, 17, 21, 29, 34, 52, 79, 107, 148, 197, 233, 366,
    #    463, 631, 827, 827, 1266, 1441, 1809, 2158, 2503, 2978, 3405, 4032, 4825, 5476, 6077, 6820, 7503
    #],
    #"population": 60E6
}

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
# Check if initialization is actually working. Does it use only E0?
# Negative number for diagnosed?????????
# Properly match Austria and Germany - see how large the parameter space for each is.
# Then match all western european countries.

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

fixed_austria = {
                    "N": 89E5,
                    "D0": 0,
                    "H0": 0,
                    "R0": 0,
                    "T0": 0,
                    "FractionContractTracing": 0.0,
                    "DayIsoDirect": lambda num: RG.lognormal(np.log(2), np.log(1.5), (num,)),
                    "DaysSymptomsToD": lambda num: RG.lognormal(np.log(25), np.log(1.5), (num,)),
                    "DaysTestingChanged": [],
                    "FractionDeceased": 0.11,

                    # Date when Health Minister said "Infection chains are no longer traceable"
                    # 10th of March: Large events cancelled
                    # 16th of March: General restrictions to meet in public
                    # 14th of April: small shops open
                    # 1st of May: large shops open
                    "DaysSocialBehaviourChanged": [23, 29, 58, 75],
                    "start_date": datetime.datetime.strptime("16.02.2020", "%d.%m.%Y"),
                    "confirmed_cases_per_day": [
                        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 3, 2, 3, 4, 4, 6, 5, 12, 33, 25, 3, 29, 51, 64,
                        115, 143, 151, 205, 156, 316, 314, 550, 453, 375, 607, 855, 796, 606, 1141, 668, 594, 522, 805,
                        564, 529, 418, 396, 241, 217, 314, 343, 329, 279, 312, 247, 130, 106
                    ],
                    "deaths_per_day": [
                        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0,
                        0, 0, 2, 0, 1, 2, 0, 2, 8, 9, 5, 4, 18, 16, 0, 18, 22, 20, 18, 12, 10, 18, 18, 16, 23, 30, 22,
                        24, 18, 13, 18,
                    ],
}

fitted_austria = {
    "E0": 40,
    "I0": 30,
    "FractionInfDiagnosed": [ 0.2, 0.2, 0.2, 0.2, 0.2 ],
    "DaysSymptomsToIsolation_Mean": [ 8, 8, 8, 8, 8 ],
    "DaysSymptomsToIsolation_Sigma": [ 1.5, 1.5, 1.5, 1.5, 1.5 ],
    "InfectiousContactsPerDay": [ 0.87, 0.22, 0.065, 0.1, 0.15 ]
}

fixed_uk = {
                    "N": 68E6,
                    "D0": 0,
                    "H0": 0,
                    "R0": 0,
                    "T0": 0,
                    "FractionContractTracing": 0.0,
                    "DayIsoDirect": lambda num: RG.lognormal(np.log(2), np.log(1.5), (num,)),
                    "DaysSymptomsToD": lambda num: RG.lognormal(np.log(25), np.log(1.5), (num,)),
                    "DaysTestingChanged": [],
                    "FractionDeceased": 0.11,

                    # Date when Health Minister said "Infection chains are no longer traceable"
                    # 23th of March: General restrictions to meet in public
                    "DaysSocialBehaviourChanged": [40],
                    "start_date": datetime.datetime.strptime("12.02.2020", "%d.%m.%Y"),
                    "confirmed_cases_per_day": [
                        0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 3, 2, 5, 13, 4, 11, 34, 30, 48, 43, 67, 48, 52,
                        83, 134, 117, 433, 251, 152, 407, 680, 647, 706, 1035, 665, 967, 1427, 1452, 2129, 2885, 2546,
                        2433, 2619, 3009, 4324, 4244, 4450, 3735, 5903, 3802, 3634, 5491, 4344, 5195, 8719, 5288, 4342
                    ],
                    "deaths_per_day": [
                        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 2, 1, 0, 4, 0,
                        11, 14, 20, 5, 43, 41, 33, 56, 48, 54, 87, 41, 115, 181, 260, 209, 180, 381, 743, 389, 684, 708,
                        621, 439, 786, 938, 881, 980, 917, 737, 717
                    ],
}

fitted_uk = {
    "E0": 40,
    "I0": 30,
    "FractionInfDiagnosed": [ 0.2, 0.2 ],
    "DaysSymptomsToIsolation_Mean": [ 8, 8 ],
    "DaysSymptomsToIsolation_Sigma": [ 1.5, 1.5 ],
    "InfectiousContactsPerDay": [ 0.87, 0.065 ]
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
    #d = Dataset.datasetForPeriod(fixed_common, fixed_germany, fitted_germany)
    d = Dataset.datasetForPeriod(fixed_common, fixed_austria, fitted_austria)
    #d = Dataset.datasetForPeriod(fixed_common, fixed_uk, fitted_uk)

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

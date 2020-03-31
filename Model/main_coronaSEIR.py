import math
import numpy as np
import scipy.integrate
import scipy.optimize
import matplotlib.pyplot as plt
import matplotlib.widgets  # Cursor
import datetime

import scipy.ndimage.interpolation  # shift function
def delay(npArray, days):
    return scipy.ndimage.interpolation.shift(npArray, days, cval=0)

# TODO:
# The curve with the dead does not match because the dead are calculated weirdly? Change that.
# Solver needs to start at point with good data, otherwise it is too sensitive to changes in initial data

# Then use the reported dead and diagnosed people to calculate beta0, beta1, i_to_d and noSymptoms
# Might make sense to add the transitions D->O O->B B->T O->R B->R (for people needing oxygen to people needing breathing apparaturs to dead people)?
# And maybe even a "A" state for the asymptomatic but infectious cases?
# Those transitions should all be governed by existing data.

incubationPeriod = 5.2
e_to_i = 1.0 / incubationPeriod  # The rate at which an exposed person becomes infective (incubation period). Note that people are and can only be tested if they have symptoms, so they are not discovered by tests before that.
timeDiagnosedToResistant = 10.0   # The rate a diagnosed recovers and moves into the resistant phase.
timeDiagnosedToDeath = 12
icuRate = 0.02
timeInHospital = 12

germany = {
    # Date when Health Minister said "Infection chains are no longer traceable"
    # 14th-16th of March (Day 26-28): Closing of schools
    # 22nd of March (Day 34): General restrictions to meet in public (the week before various restrictions depending on the individual Länder)
    "start_date":datetime.datetime.strptime("15.02.2020","%d.%m.%Y"),
    "confirmed_cases":[
        17,17,17,17,17,18,18,18,30,33,35,43,65,106,126,159,199,265,408,586,758,891,978,1303,1868,2573,3516,4883,6149,7046,8968,11825,15148,18846,22565,25603,27746,30908,34527,36471
    ],
    "deaths":[
        0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,3,4,5,7,7,10,12,17,22,32,40,44,57,72,95,111,144,152,164,182,192,197
    ],
    "dayToStartLeastSquares": 8,
    "noSymptoms": 0.7,
    "I0": 0, # Guess - the 17 were all in the resitant category at this point ( or diagnosed)
    "daysToModel": 66,
    "lockdown": 30,
    "length_of_lockdown": 60,
    "beta0": 1.0 / 0.7,
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
    "start_date":datetime.datetime.strptime("07.02.2020","%d.%m.%Y"),
    "confirmed_cases":[
        3,3,3,3,3,3,3,3,3,3,3,3,3,3,20,62,155,229,322,453,655,888,1128,1694,2036,2502,3089,3858,4636,5883,7375,9172,10149,12462,12462,17660,21157,24747,27980,31506,35713,41035,47021,53578,59138,63927,69176,74386
    ],
    "deaths":[
        0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,3,7,10,12,17,21,29,34,52,79,107,148,197,233,366,463,631,827,827,1266,1441,1809,2158,2503,2978,3405,4032,4825,5476,6077,6820,7503
    ],
    "dayToStartLeastSquares": 16,
    "noSymptoms": 0.9,
    "I0": 200, # 1 death two weeks later
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
    print(str(len(dataset["confirmed_cases"]))+'=len(dataset["confirmed_cases"]) != len(dataset["deaths"])='+str(len(dataset["deaths"])))
    exit(1)
    
for i in range(0, len(dataset["confirmed_cases"])):
    dataset["confirmed_cases"][i] = dataset["confirmed_cases"][i] - dataset["R0"]
dataset["D0"] = dataset["confirmed_cases"][0] # must be true for consistency
dataset["T0"] = dataset["deaths"][0] # must be true for consistency

logPlot = True

population = dataset["population"]

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
D_to_T = RealT[-1]/np.sum(np.asarray(RealD[0:int(-timeDiagnosedToDeath/2)]))
D_to_R = 1.0/15.0
I_to_R = 0.0

# Parameters set by external data
noSymptoms = dataset["noSymptoms"]  # https://www.reddit.com/r/COVID19/comments/ffzqzl/estimating_the_asymptomatic_proportion_of_2019/
intensiveUnits = dataset["intensiveUnits"]  # ICU units available
daysBeginLockdown = dataset["lockdown"]  # days before lockdown measures (there probably should be several of those)
daysEndLockdown = daysBeginLockdown + dataset["length_of_lockdown"]  # days before lockdown measures are relaxed (there probably should be several of those)
beta0 = dataset["beta0"] # The parameter controlling how often a susceptible-infected contact results in a new infection.
beta1 = dataset["beta1"]  # beta0 is used during days0 phase, beta1 after days0
Beta2 = dataset["beta2"]

# Parameters which might be fit to the total data of one country
i_to_d = 1.0/5.0
  # https://www.reddit.com/r/COVID19/comments/fgark3/estimating_the_generation_interval_for_covid19/
  # three days shorter because it seems there are earlier infections, goes into d_to_r
findRatio = (1 - noSymptoms) / 4  # a lot of the mild cases will go undetected  assuming 100% correct tests

# lag, whole days
communicationLag = 0
testLag = 8
symptomToHospitalLag = 5

i_to_r = noSymptoms / 5 # The rate for undiagnosed cases which recover without ever being diagnosed (very mild cases).
gamma = i_to_d + I_to_R
sigma = e_to_i

def model(Y, x, N, beta0, daysBeginLockdown, beta1, daysEndLockdown, beta2, e_to_i, i_to_d, i_to_r, d_to_r, d_to_t):
    # :param array x: Time step (days)
    # :param int N: Population
    # :param float beta: The parameter controlling how often a susceptible-infected contact results in a new infection.
    # :param float d_to_r: The rate an infected recovers and moves into the resistant phase.
    # :param float e_to_i: The rate at which an exposed person becomes infective.

    S, E, I, D, R, T = Y

    beta = beta0 if x <= daysBeginLockdown else beta1 if x <= daysEndLockdown else beta2

    dS = - beta * S * I / N
    dE = beta * S * I / N - e_to_i * E
    dI = e_to_i * E - i_to_d * I - i_to_r * I
    dD = i_to_d * I - d_to_r * D
    dR = d_to_r * D + i_to_r * I
    dT = d_to_t * D
    return dS, dE, dI, dD, dR, dT

def solve(population, daysTotal, daysBeginLockdown, daysEndLockdown, E0, I0, beta0, beta1, beta2, e_to_i, i_to_d, i_to_r, d_to_r, d_to_t):
    X = np.arange(0, daysTotal, 1 if daysTotal>0 else -1)  # time steps array

    N0 = population - E0 - I0 - D0 - R0, E0, I0, D0, R0, T0  # S, E, I, D, R at initial step
    y_data_var = scipy.integrate.odeint(model, N0, X, args=(population, beta0, daysBeginLockdown, beta1, daysEndLockdown, beta2, e_to_i, i_to_d, i_to_r, d_to_r, d_to_t))

    S, E, I, D, R, T = y_data_var.T  # transpose and unpack
    return X, S, E, I, D, R, T  # note these are all arrays

dayToStartLeastSquares = dataset["dayToStartLeastSquares"]
def solveForLeastSq(xdata):
    E0, I0, beta0, beta1, e_to_i, i_to_d = xdata

    X = np.arange(dayToStartLeastSquares, daysOfData)  # time steps array

    N0 = population - E0 - I0 - D0 - R0 - T0, E0, I0, D0, R0, T0  # S, E, I, D, R at initial step
    y_data_var = scipy.integrate.odeint(model, N0, X, args=(population, beta0, daysBeginLockdown, beta1, daysEndLockdown, Beta2, e_to_i, i_to_d, I_to_R, D_to_R, D_to_T))

    S, E, I, D, R, T = y_data_var.T  # transpose and unpack

    return 0.5*(np.log(np.cumsum(D+1)) - np.log(RealD[dayToStartLeastSquares:]+1)) + 0.5*(np.log(T+1) - np.log(RealT[dayToStartLeastSquares:]+1))

print("Starting values: E0: %.3g" % E0,"I0: %.3g" % I0, "beta0: %.3g" % beta0, "beta1: %.3g" % beta1, "e_to_i: %.3g" % e_to_i, "i_to_d: %.3g" % i_to_d, "dayToStartLeastSq: %g" % dayToStartLeastSquares)
r = scipy.optimize.least_squares(solveForLeastSq,
                                           [    E0,    I0, beta0, beta1,e_to_i,i_to_d],
                        bounds=(np.asarray([     0,     0,     0,     0,     0,1.0/10]),
                                np.asarray([np.inf,np.inf,np.inf,np.inf,np.inf,   1.0]))
                         )
E0,I0,beta0,beta1,e_to_i,i_to_d = r['x']
print("Optimised values: E0: %.3g" % E0,"I0: %.3g" % I0, "beta0: %.3g" % beta0, "beta1: %.3g" % beta1, "e_to_i: %.3g" % e_to_i, "i_to_d: %.3g" % i_to_d)

gamma = i_to_d + I_to_R
sigma = e_to_i

# https://hal.archives-ouvertes.fr/hal-00657584/document page 13
r0 = beta0 / gamma  # somehow an r0 of 3.0 seems to low
r1 = beta1 / gamma
r2 = Beta2 / gamma
s1 = 0.5 * (-(gamma + sigma) + math.sqrt((gamma + sigma) ** 2 + 4 * gamma * sigma * (r0 -1)))
print("e_to_i: %.3g" % e_to_i, "i_to_d: %.3g" % i_to_d, "I_to_R: %.3g" % I_to_R, "D_to_R: %.3g" % D_to_R, "D_to_T: %.3g" % D_to_T)
print("r0: %.2f" % r0, "   r1: %.2f" % r1, "   r2: %.2f" % r2)
print("doubling0 every ~%.1f" % (math.log(2.0, math.e) / s1), "days")

future = solve(population, daysToModel - dayToStartLeastSquares, daysBeginLockdown - dayToStartLeastSquares, daysEndLockdown - dayToStartLeastSquares, E0, I0, beta0, beta1, Beta2, e_to_i, i_to_d, I_to_R, D_to_R, D_to_T)

X, S, E, I, D, R, T = future

X = X + dayToStartLeastSquares

def print_info(i):
    print("day %d" % i)
    print(" Exposed: %d" % E[i], "%.3g" % (E[i] * 100.0 / population))
    print(" Infected: %d" % I[i], "%.3g" % (I[i] * 100.0 / population))
    print(" Diagnosed: %d" % D[i], "%.3g" % (D[i] * 100.0 / population))
    #print(" Hospital: %d" % H[i], "%.1g" % (H[i] * 100.0 / population))
    print(" Recovered: %d" % R[i], "%.3g" % (R[i] * 100.0 / population))
    print(" Deaths: %d" % T[i], "%.3g" % (T[i] * 100.0 / population))

print_info(0)
print_info(daysBeginLockdown - dayToStartLeastSquares)
print_info(daysToModel - 1 - dayToStartLeastSquares)

# Plot
fig = plt.figure(dpi=75, figsize=(20,16))
ax = fig.add_subplot(111)
if logPlot:
    ax.set_yscale("log", nonposy='clip')

#ax.plot(X, S, 'b', alpha=0.5, lw=2, label='Susceptible')
#ax.plot(X, E, 'y', alpha=0.5, lw=2, label='Exposed')
ax.plot(X, I, 'b', alpha=0.5, lw=1, label='Infectious')
ax.plot(X, D, 'g', alpha=0.5, lw=1, label='Diagnosed and isolated')
ax.plot(X, np.cumsum(D), 'm', alpha=0.5, lw=1, label='Cumulative diagnosed and isolated')
ax.plot(RealX[dayToStartLeastSquares:], RealD[dayToStartLeastSquares:], 'r', alpha=0.5, lw=1, label='Confirmed cases')
#ax.plot(X, F, color='orange', alpha=0.5, lw=1, label='Found')
#ax.plot(X, H, 'r', alpha=0.5, lw=2, label='ICU')
ax.plot(X, R, 'y', alpha=0.5, lw=1, label='Recovered with immunity')
#ax.plot(X, P, 'c', alpha=0.5, lw=1, label='Probability of infection')
ax.plot(X, T, 'k', alpha=0.5, lw=1, label='Deaths')
ax.plot(RealX[dayToStartLeastSquares:], RealT[dayToStartLeastSquares:], 'c', alpha=0.5, lw=1, label='Confirmed deaths')

#ax.plot([min(X), max(X)], [intensiveUnits, intensiveUnits], 'b-.', alpha=0.5, lw=1, label='Number of ICU available')


# actual country data
#XCDR_data = np.array(world_data.get_country_xcdr(COUNTRY, PROVINCE, dateOffset=dataOffset))

#ax.plot(XCDR_data[:,0], XCDR_data[:,1], 'o', color='orange', alpha=0.5, lw=1, label='cases actually detected in tests')
#ax.plot(XCDR_data[:,0], XCDR_data[:,2], 'x', color='black', alpha=0.5, lw=1, label='actually deceased')

#print(XCDR_data[0:30])

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
#plt.savefig('model_run.png')
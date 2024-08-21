#!/usr/bin/env python3
import time
import dcp
import numpy as np

dcp.init()

# make new job
def workfn(datum):
    dcp.progress()

    import numpy as np

    # Define two 3x3 matrices
    A = np.array([[1, 2, 3],
                  [4, 5, 6],
                  [7, 8, 9]])

    B = np.array([[9, 8, 7],
                  [6, 5, 4],
                  [3, 2, 1]])

    # Calculate the product of A and B
    product = np.dot(A, B)

    # Calculate the trace of the product
    trace = np.trace(product)

    return product

job = dcp.compute_for([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], workfn)


# add event listeners
job.on('readystatechange', print)
job.on('result', print)

@job.on('accepted')
def accepted_handler(ev):
    print(f"jobid = {job.id}")


# give job a name, require libraries for work function, add job to compute group
job.public.name = 'Bifrost2 Google Colab Example'
job.modules = ('numpy')


# deploy job, wait for it to be done, print results
setattr(__import__("__main__"), '__file__', 'ipython') # temporary workaround
job.exec()
results = job.wait()
delattr(__import__("__main__"), '__file__') # temporary workaround

print(">>>>>>>>>>>>>>>>>>>>>>>>>> RESULTS ARE IN")
print(results)


# Define two 3x3 matrices
A = np.array([[1, 2, 3],
              [4, 5, 6],
              [7, 8, 9]])

B = np.array([[9, 8, 7],
              [6, 5, 4],
              [3, 2, 1]])

# Calculate the product of A and B
product = np.dot(A, B)

print(product)

# Bifrost2 - The Python SDK for [DCP](https://www.dcp.dev/)

## Installation
```bash
pip install dcp
```

## Example

Deploying a job to DCP and getting results:
```python
import dcp
dcp.init()

# define the data your workfunction will operate on
data = [1,2,3,4,5]

# function which will execute on each datum in the dataset remotely on dcp workers
def work_function(input_datum):
	import dcp
	dcp.progress()

	# process the datum (in this exampe, square the value)
	result = input_datum * input_datum

	return result

# define the compute workload (job)
job = dcp.compute_for(data, work_function)

# add event listeners for debug logs
job.on('readystatechange', print)
job.on('accepted', lambda: print(job.id))

@job.on('result')
def on_result(event):
	print(f'New result for slice {event.sliceNumber}')
	print(event.result)

# deploy the compute workload to the DCP network
job.exec()

# wait for the compute workload to complete and process the results
results = job.wait()
print(results) # [1.0, 4.0, 9.0, 16.0, 25.0]
```
## API

### `dcp.init()`

Initializes the `dcp` module for use.

Example:
```python
import dcp
dcp.init()
```

### `dcp.compute_for(input_data: List, work_function: Union[str, Callable]) -> Job`

Instantiates a job handle.

### `dcp.compute.Job`

Job class, instances are returned by the factory functions `dcp.compute_for`, `dcp.compute.do` and from the `@dcp.distribute(...)` decorator.

#### Job Methods
**`job.exec(slicePaymentOffer=compute.marketValue: float, paymentAccountKeystore=wallet.get(): dcp.wallet.Keystore, initialSliceProfile=none: dict) -> None`**

Deploys the job to the DCP Network.
`slicePaymentOffer` specifies how many DCCs will be expended per slice.
Once a job is deployed, workers will begin picking up slices of the job to compute.

**`job.wait() -> ResultHandle`**

Waits for a job to complete.
Returns a List-like ResultHandle object which can be used to access the results of the computation.

**`job.on(event_name: str, callback_fn: Callable[[dict], None]) -> None`**

Registers a callback function to execute each time a job event is triggered.

Example: `job.on('result', print)` will print a result each time there is a result event.

**`job.on(event_name: str) -> FunctionDecorator`**

Registers a callback function to execute each time a job event is triggered as a decorator.

Example:
```python
@job.on('accepted')
def on_accepted_callback(event):
  print(f"Job {job.id} has been submitted to the DCP Network for computation")
```

#### Job Attributes
**`job.autoClose`**

Whether or not the job will remain open to accepting more slices after it has been deployed.
See "Open and Closed Jobs" in the Concepts section as well as `dcp.job.addSlices` and `dcp.job.fetchResults`.
By default, `job.autoClose` is `True`, meaning the job will not allow additional slices to be added.
So long as a job is "open", it can receive additional slices to be computed at any point in the future.

Example:
```python
my_job.autoClose = False
my_job.exec # deploy the job
dcp.job.addSlices([1,2,3], my_job.id) # add three new slices to the job
```

**`job.computeGroups`**

List of Dictionaries with `joinKey` and `joinSecret` keys.
By default, `job.computeGroups` will contain a single dictionary element which will include the credentials for the global / public DCP Compute Group; it can be overridden if deploying to the global / public DCP Compute Group is not desired.

Example: `job.computeGroups = [{ 'joinKey': 'my cg', 'joinSecret': 'my epic password' }]` will deploy your job only to the imaginary "my cg" compute group.

Example: `job.computeGroups.append({ 'joinKey': 'my cg', 'joinSecret': 'my epic password' })` will deploy your job only to both the "public" and "my cg" compute groups.

**`job.fs`**

An instance of `dcp.JobFS`.
Used to add and manage the files that will be uploaded as part of the job. DCP Workers will download the files so they are available for use in your work function.
Currently only available for use in the "pyodide" Worktime.

Example:
```python
job.fs.add(‘~/Downloads/will_kantor_pringle.png’) # Goes to current working directory of the VFS plus the basename of the file being added (/home/pyodide/will_kantor_pringle.png)
job.fs.add(‘~/Downloads/severn_lortie.png’, ‘./vfs/at/dir/filename.png’) # goes to (/home/pyodide/vfs/at/dir/filename.png), creates directoies if they do not exist
job.fs.add(‘~/Downloads/wes_garland.png’, ‘/absolute_file.png’) # goes to (/absolute_file.png)
job.fs.chdir(‘./vfs/at/dir/’) # throws if any directories in the path do not exist
```

**`job.public`**

A dictionary with three keys: "public", "description", and "link" which each map to strings.
These attributes are displayed by some DCP Workers while operating on slices of the corresponding Job.

Example: `job.public.name = "Will's Awesome DCP Job"`

**`job.worktime`**

A string specifying the Worktime which will be used to execute the Work Function inside of.
By default, `job.worktime` will be set to `"pyodide"`, the Pyodide Worktime for executing Python Work Functions in DCP.

Example: `job.worktime = 'map-basic'` will set the worktime to JavaScript, and a string of a JavaScript function can be specified as the Work Function.

**`job.worktimeVersion`**

A string specifying a semver Worktime version to use.

**`job.customWorktime`**

A boolean specifying if the worktime to use is custom or officially supported by DCP.

<!--
### `dcp.compute.getJobInfo()`

### `dcp.compute.status()`
-->

### `dcp.job.addSlices(slice_data: List, job_id: str)`

Adds slices to a job already deployed to DCP.

Example: `dcp.job.addSlices(['Hello, 'World'], '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')` will add two slices to the job referred to by that job ID.

### `dcp.job.fetchResults(job_id: str, range_object: dcp.compute.RangeObject) -> List`

Gets the results for a job over specified slice number ranges.

### `dcp.JobFS`

A JobFS (Job Filesystem) class for adding files to the Pyodide in-memory filesystem.
The filesystem is uploaded and accessible at job run time.

Example: `fs = dcp.JobFs()`

#### JobFs Methods

**`fs.add(source: Union[str, Path, bytes], destination: Optional[str]) -> None`**

Adds a file to the filesystem.
`source` can either be a path on the deployer's local file system or a bytes buffer in memory. 
The destination's path is resolved to the current working directory of the fs, initially `/home/pyodide`.


**`fs.chdir(destination: str) -> None`**

Changes the current working directory to another directory.
Throws an exception if the directory passed as `destination` doesn't exist.

### `dcp.wallet.get(label: Optional[str]) -> dcp.wallet.Keystre`

Gets a dcp keystore.

<!--
## Concepts

Job

Work Function

Slice

Compute Groups

Worktime

DCP Worker

DCP Network

DCCs and the DCP Compute Market

Open and Closed Jobs
-->

## Contributing

### Build

Install [Poetry](https://python-poetry.org/), then in the root of the project directory run the following:
- `$ poetry install`
- `$ poetry shell`

Verify your installation is correct by running the test suite:
- `$ poetry run pytest`

### Tests

Run tests with:
- `$ poetry run pytest`

### Publishing

We need to upload the tar since we need to run `npm install` after installation - this is not possible with the wheel distribution option.
- `$ poetry build -f sdist`
- `$ twine upload dist/dcp-<new-version-here>.tar.gz`

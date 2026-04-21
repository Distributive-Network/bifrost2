from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import json

import dcp; dcp.init()

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = int(self.path.strip('/'))
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(path).encode())

#start http server on seperate thread
server_address = ("localhost", 12345)
httpd = HTTPServer(server_address, SimpleHandler)
print("Server running at http://localhost:12345")
server_thread = threading.Thread(target=httpd.serve_forever)
server_thread.daemon = True 
server_thread.start()

def workfn(x):
    import dcp
    dcp.progress()
    return x * x


# 'http://localhost:12345' must be added to a Worker's allowed origins for slices to be completed
# run worker.originManager.add('http://localhost:12345', null, null) in the console, or edit the worker config
# On the public group the job will encounter many errors since workers by default can't access that URL
my_rdp = dcp.compute.RemoteDataPattern('http://localhost:12345/{slice}',5)
my_j =  dcp.compute_for(my_rdp, workfn)


# add event listeners
my_j.on('readystatechange', print)
my_j.on('result', print)
my_j.on('error', print)

@my_j.on('accepted')
def accepted_handler(ev):
    print(f"jobid = {my_j.id}")

my_j.public.name = 'simple bifrost2 remote data pattern example'

my_j.exec()
res = my_j.wait()

print(">>>>>>>>>>>>>>>>>>>>>>>>>> RESULTS ARE IN")
print(res)

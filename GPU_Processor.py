''' =======================================================================
    GPU Processor
        Exposes functionality which the GPU-rpc-server will use.
        Using pyOpenCL to handle processing
    ======================================================================= '''
from util import timing

import pyopencl as cl
import numpy
import random

''' =======================================================================

    Functionality

    ======================================================================= '''
# ----------------------------------------------------------------------------
#
# Data loader
#
# ----------------------------------------------------------------------------
def load_data():
    '''Loads tax data and creates NumPy arrays for it. This should be called
    only once, when a CL object is created.  Data could be loaded from
    a file, database, etc. In this example, each data item is a NumPy array.
    '''
    num_items = 100000

    # Shape of data
    data_dict = {
        'income': numpy.array([abs(random.gauss(90000, 45000)) for i in xrange(num_items)], 
            dtype=numpy.float32),
        'capGains': numpy.array([abs(random.gauss(20000, 4000)) for i in xrange(num_items)], 
            dtype=numpy.float32),
        'fillingStatus': numpy.array([random.randint(0,4) for i in xrange(num_items)], 
            dtype=numpy.float32),
        'dividendsInterest': numpy.array([abs(random.gauss(50000, 45000)) for i in xrange(num_items)], 
            dtype=numpy.float32),
        'children': numpy.array([random.randint(0,4) for i in xrange(num_items)],
            dtype=numpy.float32),
    }

    # Load all the record data from a file. Each record is a person with
    #   an income, cap gains, num dependents, etc.
    

    return data_dict

class CL:
    def __init__(self):
        self.data = load_data()

        self.ctx = cl.create_some_context()
        self.queue = cl.CommandQueue(self.ctx)

        self.setup_buffers()

    def setup_buffers(self):
        '''Sets up the data arrays and buffers. This needs to happen 
        only once, as the data itself does not change
        '''

        #initialize client side (CPU) arrays
        timing.timings.start('buffer')
        print 'Setting up data arrays'

        #Get data from arrays
        timing.timings.stop('buffer')

        print 'Done setting up two numpy arrays in %s ms | (%s seconds)' % (
            timing.timings.timings['buffer']['timings'][-1],
            timing.timings.timings['buffer']['timings'][-1] / 1000
        )

        timing.timings.start('buffer')

        #create OpenCL buffers
        mf = cl.mem_flags

        self.income_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
            hostbuf=self.data['income'])
        self.capGains_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
            hostbuf=self.data['capGains'])
        self.dividendsInterest_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, 
            hostbuf=self.data['dividendsInterest'])
        self.children_buf = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR,
            hostbuf=self.data['children'])

        # Destination buffer must be same size as the input buffer
        self.dest_buf = cl.Buffer(self.ctx, mf.WRITE_ONLY,
            self.data['income'].nbytes)

        timing.timings.stop('buffer')

        print 'Done setting up buffers in %s ms' % (
            timing.timings.timings['buffer']['timings'][-1]
        )

    def load_program(self, params):
        ''' Create the .cl program to use. This needs to get regenerated at each
        request, as the values used change based on the request
        '''

        #Generate a .cl program
        program = """
        __kernel void worker(
            __global float* data_income, 
            __global float* data_capGains, 
            __global float* data_dividendsInterest, 
            __global float* data_children, 
            __global float* result
            )
        {
            unsigned int i = get_global_id(0);
            float d1 = data_income[i];
            float d2 = data_capGains[i];
        """

        # Define calculation based on passed in params. The data arrays are 
        #   static
        program += """result[i] = d1 * d2 * {income};
        """.format(
                income=params['income']
            )

        program += "}" 

        #create the program
        self.program = cl.Program(self.ctx, program).build()


    def execute(self, params):
        ''' This handles the actual execution for the processing, which would
        get executed on each request - this is where we care about the
        performance
        '''

        timing.timings.start('load')
        self.load_program(params)
        timing.timings.stop('load')
        finish = timing.timings.timings['load']['timings'][-1]
        print '<<< Loaded program in %s ms' % (finish)

        timing.timings.start('execute')
        # Start the program
        self.program.worker(self.queue, 
            self.data['income'].shape,
            None,
            self.income_buf,
            self.capGains_buf,
            self.dividendsInterest_buf,
            self.children_buf,
            self.dest_buf,
        )

        # Get an empty numpy array in the shape of the original data
        result = numpy.empty_like(self.data['income'])

        #Wait for result
        cl.enqueue_read_buffer(self.queue, self.dest_buf, result).wait()

        #show timing info
        timing.timings.stop('execute')
        finish = timing.timings.timings['execute']['timings'][-1]
        print '<<< Executed in %s ms' % (finish)
        return result

# Execute it
# ---------------------------------------
if __name__ == "__main__":
    # Test that execute works when calling this directly passing in a param
    example = CL()
    print example.execute({ 'income': 42 })

import time
import functools

def decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("before running function")
        res = func(*args, **kwargs)
        print("result is {}".format(res))
        print("after running function")
        return res
    
    return wrapper

@decorator
def test(a, b):
    return a + b

#test(2, 3)
#x = decorator(test)(2, 3)

#x = decorator(test) # it return wrapper
#print(x.__name__)

print(test.__name__)

---------------------------------------------------
# again insert into another function
def decoratorWithArgument(param):
    def inner(func):
        def wrapper(*args, **kwargs):
            print("before running function")
            res = func(*args, **kwargs) * param
            print("result is {}".format(res))
            print("after running function")
            return res
        return wrapper
    return inner

@decoratorWithArgument(10)
def test(a, b):
    return a + b
test(2, 3)
#result is 50, (2+3)*10

-------------------------------------------------------------------
def timeIt(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        startTime = time.time()
        result = func(*args, **kwargs)
        endTime = time.time()
        print("{} executed in {} seconds".format(func.__name__, endTime - startTime:.6f))
        return result
    return wrapper

@timeIt
def test1(num):
    for i in range(num):
        print(i)

test1(1000)


















import math

def rolling_summary(values, width, min_valid=1):
    data=list(values)
    if isinstance(width,bool) or not isinstance(width,int) or width<=0 or width>len(data): raise ValueError('invalid width')
    if isinstance(min_valid,bool) or not isinstance(min_valid,int) or not 1<=min_valid<=width: raise ValueError('invalid min_valid')
    for value in data:
        if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)):
            raise ValueError('invalid value')
    result=[]
    for start in range(len(data)-width+1):
        present=[v for v in data[start:start+width] if v is not None]
        enough=len(present)>=min_valid
        result.append({'start':start,'count':len(present),'mean':sum(present)/len(present) if enough else None,
                       'min':min(present) if enough else None,'max':max(present) if enough else None})
    return result

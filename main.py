# import Fastapi class from fastapi  
from fastapi import FastAPI, Path, HTTPException, Query
from fastapi.responses import JSONResponse
import json
from pathlib import Path as FilePath
import shutil
# we will import annotated to add description from typing module
from typing import Annotated, Literal, Optional  # to make user experience better
from pydantic import BaseModel, Field, computed_field  # we need it to create post api

#==============================================================================
class Patient(BaseModel): # this patient class inherits from BaseModel class
    id: Annotated[str, Field(..., description='ID of Patient', examples=['P001'])]
    name: Annotated[str, Field(..., description='Name of Patient')]
    city: Annotated[str, Field(..., description='Name of city')]
    age: Annotated[int, Field(..., gt=0, lt=120, description='Age of Patient')]
    gender: Annotated[Literal['male', 'female', 'others'], Field(..., description='Gender of Patient')]
    height: Annotated[float, Field(..., gt=0, description='Height of Patient in meters')]
    weight: Annotated[float, Field(..., gt=0, description='Weight of Patient in Kg')]
    # computed =Field , can compute dynamic field from existing field 
    @computed_field
    @property
    def bmi(self) -> float:
        bmi = round(self.weight / (self.height**2), 2)
        return bmi
    # based on bmi we want to add verdict like underweight , overweight etc

    @computed_field
    @property
    def verdict(self) -> str:
        if self.bmi < 18.5:
            return 'Underweight'
        elif self.bmi < 30:
            return 'Normal'
        else:
            return 'Obese'





#=====================================================================
# we will build new pydantic model for updation
class PatientUpdate(BaseModel):
    # we excluded patient_id because its part of path parameter , not part of request body
    # Optional use krne ka ek hi maksad hai ki , user update krna chaie to kre nhi to koi bat nhi isi liye default none hai
    name: Annotated[Optional[str], Field(default=None)]
    city: Annotated[Optional[str], Field(default=None)]
    age: Annotated[Optional[int], Field(default=None, gt=0, lt=120)]
    gender: Annotated[Optional[Literal['male', 'female', 'others']], Field(default=None)]
    height: Annotated[Optional[float], Field(default=None, gt=0)]
    weight: Annotated[Optional[float], Field(default=None, gt=0)]
 


#
app = FastAPI(title="Patient Management System", version="0.1.0")

DATA_FILE = FilePath(__file__).resolve().parent / 'patients.json'
EXAMPLE_DATA_FILE = FilePath(__file__).resolve().parent / 'patients.json.example'

#=============================================================================
# load data from patients.json with safe fallback
def load_data() -> dict:
    if not DATA_FILE.exists():
        if EXAMPLE_DATA_FILE.exists():
            shutil.copy(EXAMPLE_DATA_FILE, DATA_FILE)
        else:
            save_data({})
            return {}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def save_data(data: dict) -> None:
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
#===================================================================================

# retrieve ==> get
# crete a route for end point 
@app.get("/")
def hello():
    return ({'message': 'Hey, i came into reality'})

# second end point 
@app.get('/about')
def about():
    return ({'message': 'Hey i am trying to see patient data'})

# create an end point view
@app.get('/view')
def view():
    # fetch data using , load_data function
    data = load_data()
    return data



@app.get('/patient/{patient_id}')
def view_patient(patient_id: str = Path(..., description="ID of patient in DB", examples=['P001'])):
    #load data
    data = load_data()

    if patient_id in data:
        return data[patient_id]
    raise HTTPException(status_code=404, detail='patient not found')

@app.get('/sort')
def sort_patient(
    sort_by: str = Query(..., description='Sort on basis of height, weight or bmi'),
    order: str = Query('asc', description='Sort in asc or desc order')
):
    valid_fields = ['height', 'weight', 'bmi']
    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail=f'invalid field select from {valid_fields}')

    if order not in ['asc', 'desc']:
        raise HTTPException(status_code=400, detail='invalid order select between asc and desc')
    data = load_data()

    sort_order = True if order == 'desc' else False

    sorted_data = sorted(data.values(), key=lambda x: x.get(sort_by, 0), reverse=sort_order)
    return sorted_data



#===========================================================================================
#create --> POST
@app.post('/create')
def create_patient(patient:Patient):# sab kuch dene se accha hai , patient ko de do , jisme sa kuch pahle se define hai aur data validation alag se kr dega 
    #-------> patient is pydantic object
    #load existing data----------> which is pydantic dictionary
    data=load_data()
    # check if patient already exist or not 
    if patient.id in data:
        raise HTTPException(status_code=400,detail='Patient already exist')

    # add new patient to data base
    #----> to add new data we have to convert pydantic obj into dictionary
    data[patient.id]=patient.model_dump(exclude=['id']) # convert pydantic into dictionary--> everything is coming including bmi and verdict
    # now --->data[patient.id] is dictionary

    # now save it into json , hamare pass save func alreay pada hai
    save_data(data)
    # ab chuki hmko ye response json format mai bhejna hai --> aur json response mai do chije bhejte hai , status code  and content (jo ki dictionary hai)

    return JSONResponse(status_code=201,content={'message':'Patient data created successfully '})


#=====================================================================================================
#update=> put
@app.put('/edit/{patient_id}')
def update_patient(patient_id:str,patient_update:PatientUpdate):
    # load data
    data=load_data()
    # check if data already exist in database or not
    if patient_id not in data:
        raise HTTPException(status_code=404,detail='Patient not found')
    #convert pydatic obj into python dictiionary
    existing_patient_info=data[patient_id] #isme sari field hai
    updated_patient_info=patient_update.model_dump(exclude_unset=True) # sirf city and weight 

    for key,value in updated_patient_info.items():# extracting key,value
        # loop chala the hai update wale pr pr changes kr rhe hai existing may
        existing_patient_info[key]=value
    # covert this dictionary into pydantic object---> updated dmi and verdict --> pydantic obj ---> dict 
    existing_patient_info['id']=patient_id
    patient_pydantic_obj=Patient(**existing_patient_info)# ye line error degi kyo ki isme patient id nahi is liye pahle isme patient id add kro

    # pydantic obj to dict
    existing_patient_info=patient_pydantic_obj.model_dump(exclude=['id'])# because we don;t need id 

    # add in data
    data[patient_id]=existing_patient_info
    # save data
    save_data(data)

    return JSONResponse(status_code=200,content={'message':'patient_updated'})


#======================================================================================
#delete method
@app.delete('/delete/{patient_id}')
def delete_patient(patient_id:str):
    # load data
    data=load_data()

    if patient_id not in data:
        raise HTTPException(status_code=404,detail='Patient not found')
    del data[patient_id]
    save_data(data)

    return JSONResponse(status_code=200,content={'message':'patient data deleted successfully'})
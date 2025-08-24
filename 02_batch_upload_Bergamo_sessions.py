#%%
import os
import numpy as np
from datetime import datetime

import json
import pandas as pd
from aind_data_access_api.document_db import MetadataDbClient

def query_mouse_from_docdb(subject_id):
    API_GATEWAY_HOST = "api.allenneuraldynamics.org"
    DATABASE = "metadata_index"
    COLLECTION = "data_assets"
    
    docdb_api_client = MetadataDbClient(
        host=API_GATEWAY_HOST,
        database=DATABASE,
        collection=COLLECTION,
    )
    
    filter_query = {"subject.subject_id": str(subject_id)}
    projection = {
        "name": 1,
        "created": 1,
        "location": 1,
        "last_modified": 1,
        "session": 1,
    }
    records = docdb_api_client.retrieve_docdb_records(
        filter_query=filter_query,
        projection=projection,
    )
    return records

#vast_dir_base = '/home/rozmar/Network/Vast/scratch/BCI/2p-raw'
vast_dir_base = '/home/rozmar/Network/Allen/aind/scratch/BCI/2p-raw'
subject_folders = os.listdir(vast_dir_base )
filenum = []
session_json_present = []
suite2p_folder_present = []
subject_names = []
session_names = []
tiff_filenum = []
session_json_filenums = []
for subject in subject_folders:
    if '.' in subject:
        continue
    if 'BCI' in subject:
        print(subject)
        subject_folder = os.path.join(vast_dir_base ,subject)
        sessions = os.listdir(subject_folder)
        for session in sessions:
            if '.' in session:
                continue
            try:
                session_date = datetime.strptime(session, '%m%d%y').date()
            except:
                continue
            session_folder = os.path.join(vast_dir_base ,subject,session)
            files = os.listdir(session_folder)
            tifnum = 0
            for f in files:
                if f.endswith('.tif'):
                    tifnum +=1
                
                    
            filenum.append(len(files))
            if  'session.json' in files:
                session_json_present.append(True)
                with open(os.path.join(session_folder,'session.json'), "r") as f:
                    metadata_now= json.load(f)
                filenum_ = 0
                for ds in metadata_now['data_streams']:
                    if metadata_now['data_streams'][0]['stack_parameters'] != None: # we assume a single stack file (there is no stim epoch for stack)
                        filenum_+=1
                for se in metadata_now['stimulus_epochs']:
                    try:
                        filenum_ += len(se['output_parameters']['tiff_files'])
                    except:
                        pass
                session_json_filenums.append(filenum_)
                
            else:
                session_json_present.append(False)
                session_json_filenums.append(np.nan)
                
            if 'suite2p' in files:
                suite2p_folder_present.append(True)
            elif 'ophys' in files:
                files_ = os.listdir(os.path.join(vast_dir_base ,subject,session,'ophys'))
                if 'suite2p' in files_:
                    suite2p_folder_present.append(True)
                else:
                    suite2p_folder_present.append(False)
                for f in files_:
                    if f.endswith('.tif'):
                        tifnum +=1
            elif 'pophys' in files:
                files_ = os.listdir(os.path.join(vast_dir_base ,subject,session,'pophys'))
                if 'suite2p' in files_:
                    suite2p_folder_present.append(True)
                else:
                    suite2p_folder_present.append(False)
                for f in files_:
                    if f.endswith('.tif'):
                        tifnum +=1
            else:
                suite2p_folder_present.append(False)
            subject_names.append(subject)
            session_names.append(session)
            tiff_filenum.append(tifnum)
            #print([session,len(files )])
#%%
subject_names = np.asarray(subject_names)
session_names = np.asarray(session_names)
suite2p_folder_present = np.asarray(suite2p_folder_present)
filenum = np.asarray(filenum)
session_json_present = np.asarray(session_json_present)
tiff_filenum = np.asarray(tiff_filenum)
session_json_filenums = np.asarray(session_json_filenums)


#%% find sessions that are both uploaded and analyzed
sum(np.asarray(suite2p_folder_present)&np.asarray(session_json_present))

metadata_file = '/home/rozmar/Network/AmazonS3/aind_scratch/aind-scratch-data/BCI/metadata_060424/Surgeries-BCI.csv'
metadata_df = pd.read_csv(metadata_file)
metadata_df.pop('Unnamed: 0')

potential_sessions_needed = session_json_present#suite2p_folder_present&session_json_present # potential folders for deletion
database_dict = {}
for idx in np.where(potential_sessions_needed )[0]:
    try:
        subject_id = int(metadata_df.loc[metadata_df['ID']==subject_names[idx],'animal#'].values[0])
    except:
        print('{} not found in google metadata'.format(subject_names[idx]))
        continue
    if subject_names[idx] not in database_dict .keys():
        database_dict[subject_names[idx]] = {}
    
    records = query_mouse_from_docdb(subject_id)
    record_days = []
    isprocessed = []
    for r in records:
        try:
            record_days.append(datetime.strptime(r['session']['session_start_time'],"%Y-%m-%dT%H:%M:%S.%f%z").date())
        except:
            record_days.append(np.nan)
        isprocessed.append('processed' in r['name'])
    print('{} - {}'.format(subject_names[idx],session_names[idx]))
    
    database_dict[subject_names[idx]][session_names[idx]]={}
    database_dict[subject_names[idx]][session_names[idx]]['data_assets'] = {}
    database_dict[subject_names[idx]][session_names[idx]]['local_tiff_file_num'] = tiff_filenum[idx]
    database_dict[subject_names[idx]][session_names[idx]]['local_json_tiff_file_num'] = session_json_filenums[idx]
    
    record_days = np.asarray(record_days)
    isprocessed = np.asarray(isprocessed)
    needed_records= (record_days == datetime.strptime(session_names[idx], '%m%d%y').date()) & (isprocessed == False)
    if sum(needed_records)>1:
        print('too many raw datasets')
        print('{} local tiffs'.format(tiff_filenum[idx]))
        for r in np.asarray(records)[needed_records]:
            filenum = 0
            for ds in r['session']['data_streams']:
                if r['session']['data_streams'][0]['stack_parameters'] != None: # we assume a single stack file (there is no stim epoch for stack)
                    filenum+=1
            for se in r['session']['stimulus_epochs']:
                try:
                    filenum += len(se['output_parameters']['tiff_files'])
                except:
                    pass
            print('{} - {} files'.format(r['name'],filenum))
            database_dict[subject_names[idx]][session_names[idx]]['data_assets'][r['name']] = {'tiff_file_num':filenum}  
            
    
    if sum(needed_records)==0:
        print('no corresponding dataset in docdb')
        continue
    r = np.asarray(records)[needed_records][0]
    filenum = 0
    for ds in r['session']['data_streams']:
        if ds['stack_parameters'] != None: # we assume a single stack file (there is no stim epoch for stack)
            filenum+=1

    for se in r['session']['stimulus_epochs']:
        try:
            filenum += len(se['output_parameters']['tiff_files'])
        except:
            pass
    database_dict[subject_names[idx]][session_names[idx]]['data_assets'][r['name']] = {'tiff_file_num':filenum}  
    print('{} local vs {} remote'.format(tiff_filenum[idx],filenum))




#%%

session_ready_for_deletion= []
#data_assets_to_be_deleted = []
sessions_to_be_reuploaded = []
sessions_uploaded_fine = []
sessions_to_be_uploaded = []
for subject in database_dict.keys():
    for session in database_dict[subject].keys():# check if session date matches
        data_assets = list(database_dict[subject][session]['data_assets'].keys())
        
        local_filenum = database_dict[subject][session]['local_tiff_file_num']
        local_json_filenum = database_dict[subject][session]['local_json_tiff_file_num']
        if len(data_assets)==0:
            if (local_json_filenum>=local_filenum-10) and (local_json_filenum<local_filenum+10):
                sessions_to_be_uploaded.append({'subject':subject,
                                                   'session':session,
                                                'local_filenum':local_filenum,
                                                'remote_filenum':0,
                                                'local_json_filenum':local_json_filenum})
            
            continue
        if len(data_assets)>1:
            remote_filenums = []
            
            for da in data_assets:
                remote_filenums.append(database_dict[subject][session]['data_assets'][da]['tiff_file_num'])
            
        else:
            remote_filenums = [database_dict[subject][session]['data_assets'][data_assets[0]]['tiff_file_num']] 
        remote_filenums = np.asarray(remote_filenums)
        if  any(remote_filenums>= local_filenum-10):
            session_ready_for_deletion.append({'subject':subject,
                                               'session':session,
                                               'local_filenum':local_filenum,
                                               'remote_filenum':remote_filenums,
                                               'local_json_filenum':local_json_filenum})
        else:
            sessions_to_be_reuploaded.append({'subject':subject,
                                               'session':session,
                                               'local_filenum':local_filenum,
                                               'remote_filenum':remote_filenums,
                                               'local_json_filenum':local_json_filenum})\
        #%%
import matplotlib.pyplot as plt
#%matplotlib qt
sum(session_json_filenums>=tiff_filenum)
fig = plt.figure()
ax1 = fig.add_subplot(2,1,1)
plt.plot(tiff_filenum,session_json_filenums,'ko')
plt.xlabel('real tiff filenum')
plt.ylabel('tiff filenum in local json (black) / aws (red)\n to be uploaded (blue)')
    #%
for mouse in database_dict.keys():
    for session in database_dict[mouse].keys():
        #print(database_dict[mouse][session])
        if len(database_dict[mouse][session]['data_assets'].keys())>0:
            aws_filenum = database_dict[mouse][session]['data_assets'][list(database_dict[mouse][session]['data_assets'].keys())[0]]['tiff_file_num']
            plt.plot(database_dict[mouse][session]['local_json_tiff_file_num'],
                     aws_filenum,
                     'r.')
for s in sessions_to_be_uploaded:
    plt.plot(s['local_filenum'],
             s['local_json_filenum'],
             'b.')
ax2 = fig.add_subplot(2,1,2)           
diff_tiff = session_json_filenums-tiff_filenum
diff_tiff[diff_tiff >25] = 25
diff_tiff[diff_tiff <-25] = -25
ax2.hist(diff_tiff,100)
plt.xlabel('json filenum - tiff filenum')
#%% 
import pandas as pd
good_df = pd.DataFrame.from_dict(session_ready_for_deletion)
bad_df = pd.DataFrame.from_dict(sessions_to_be_reuploaded)
good_df.to_csv(os.path.join(vast_dir_base,'uploaded_assets.csv'))
#%% upload to AWS
from aind_data_transfer_service.models.core import (
    UploadJobConfigsV2,
    SubmitJobRequestV2,
    Task
)
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
from typing import Optional
import traceback, os, json, traceback, shutil, requests
import time

for s in sessions_to_be_uploaded:
    session_folder = os.path.join(vast_dir_base ,s['subject'],s['session'])
    with open(os.path.join(session_folder,'session.json'), "r") as f:
        metadata_now= json.load(f)
    
    thisMouse = s['subject']
    dateEnteredAs = s['session']
    subject_id = metadata_now['subject_id']
    service_url = "http://aind-data-transfer-service/api/v2/submit_jobs" # For testing purposes, use http://aind-data-transfer-service-dev/api/v2/submit_jobs
    project_name = "Brain Computer Interface"
    s3_bucket = "default"
    platform = Platform.SINGLE_PLANE_OPHYS
    job_type = "default"
    
    codeocean_pipeline_id = "a2c94161-7183-46ea-8b70-79b82bb77dc0"
    codeocean_pipeline_mount: Optional[str] = "ophys"
    
    pophys_task = Task(
        job_settings={
            "input_source": f"//allen/aind/scratch/BCI/2p-raw/{thisMouse}/{dateEnteredAs}/pophys"
        }
    )
    behavior_video_task = Task(
        job_settings={
            "input_source": f"//allen/aind/scratch/BCI/2p-raw/{thisMouse}/{dateEnteredAs}/behavior_video"
        }
    )
    behavior_task = Task(
        job_settings={
            "input_source": f"//allen/aind/scratch/BCI/2p-raw/{thisMouse}/{dateEnteredAs}/behavior"
        }
    )
    
    modality_transformation_settings = {
        Modality.POPHYS.abbreviation: pophys_task,
        Modality.BEHAVIOR_VIDEOS.abbreviation: behavior_video_task,
        Modality.BEHAVIOR.abbreviation: behavior_task
    }
    
    gather_preliminary_metadata = Task(
        job_settings={
            "metadata_dir": (
                f"/allen/aind/scratch/BCI/2p-raw/{thisMouse}/{dateEnteredAs}"
            )
        }
    )
    
    pophys_codeocean_pipeline_settings = Task(
        skip_task=False,
        job_settings={
            "pipeline_monitor_settings": {
                "run_params": {
                    "data_assets": [{"id": "", "mount": codeocean_pipeline_mount}],
                    "pipeline_id": codeocean_pipeline_id,
                }
            }
        }
    )
    
    codeocean_pipeline_settings = {
        Modality.POPHYS.abbreviation: pophys_codeocean_pipeline_settings
    }
    
    #adding codeocean capsule ID and mount
    modalities =[Modality.POPHYS, Modality.BEHAVIOR]
    if 'side' in os.listdir(os.path.join(session_folder,'behavior_video')):
        if len(os.listdir(os.path.join(session_folder,'behavior_video','side')))>0:
            modalities.append(Modality.BEHAVIOR_VIDEOS)

    upload_job_configs = UploadJobConfigsV2(
        job_type=job_type,
        s3_bucket=s3_bucket,
        platform=platform,
        subject_id=subject_id,
        acq_datetime=datetime.strptime(
            metadata_now['session_start_time'], "%Y-%m-%dT%H:%M:%S.%f%z"
        ).strftime("%Y-%m-%d %H:%M:%S"),
        modalities=modalities,
        project_name=project_name,
        tasks={
            "modality_transformation_settings": modality_transformation_settings,
            "gather_preliminary_metadata": gather_preliminary_metadata,
            "codeocean_pipeline_settings": codeocean_pipeline_settings,
        },
    )
    
    upload_jobs = [upload_job_configs]
    submit_request = SubmitJobRequestV2(upload_jobs=upload_jobs)
    post_request_content = submit_request.model_dump(
        mode="json", exclude_none=True
    )
    
    #Submit request
    submit_job_response = requests.post(url=service_url, json=post_request_content)
    print(submit_job_response.status_code)
    print(submit_job_response.json())
    print('waiting 1 minut before next upload')
    time.sleep(60)
    

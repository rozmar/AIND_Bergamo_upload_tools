#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The purpose of this script is to 
- run through all sessions on VAST

@author: rozmar
"""

# -*- coding: utf-8 -*-
"""
This code is intended to update all the datasets on VAST, then send to CO
"""
#%%
import traceback, os, json, traceback, shutil, requests
from pathlib import Path, PurePosixPath
import numpy as np
from datetime import datetime
from glob import glob
from aind_metadata_mapper.bergamo.session import ( BergamoEtl, 
                                                  JobSettings,
                                                  )
#%

from aind_data_transfer_models.core import (
    ModalityConfigs,
    BasicUploadJobConfigs,
    SubmitJobRequest,
)
from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.platforms import Platform
import subprocess
#from main_utility import *
os.chdir('/home/rozmar/Scripts/AIND_Bergamo_upload_tools')
import bergamo_rig
from main_utility import *
import pandas as pd
import subprocess
import os
import signal
import sys

#%%
extract_behavior = True
stage_videos = True
create_rig_json = True
create_session_json = True
move_files_to_pophys = True
metadata_file = '/home/rozmar/Network/AmazonS3/aind_scratch/aind-scratch-data/BCI/metadata_060424/Surgeries-BCI.csv'
metadata_df = pd.read_csv(metadata_file)
metadata_df.pop('Unnamed: 0')
dataDir = '/home/rozmar/Network/Allen/aind/scratch/BCI/2p-raw/' 
mice = os.listdir(dataDir )
filenum_in_folder = []
pophys_in_files = []

try:
    video_staging_failed
except: # if the variable doesn't exist, we make it
    video_staging_failed= []
try:
    long_behavior_extraction
except: # if the variable doesn't exist, we make it
    long_behavior_extraction= []
try:
    no_behavior_extraction
except: # if the variable doesn't exist, we make it
    no_behavior_extraction= []
too_many_files = []
try:
    session_json_problem
except: # if the variable doesn't exist, we make it
    session_json_problem= []
for mouse in mice:
    if 'BCI' in mouse:
        print(mouse)
        import pandas as pd
        
        try:
            subject_id = int(metadata_df.loc[metadata_df['ID']==mouse,'animal#'].values[0])
        except:
            print('mouse not found in surgery spreadsheet: {}'.format(mouse))
            continue
        sessions = os.listdir(os.path.join(dataDir,mouse))
        for session in sessions:
            if '.' in session:
                continue
            files = os.listdir(os.path.join(dataDir,mouse,session))
            filenum_in_folder.append(len(files))
            pophys_in_files.append('pophys' in files or 'ophys' in files)
            if len(files)>10:
                print('too many files {}'.format(len(files)))
                session_folder = os.path.join(dataDir,mouse,session)
                too_many_files .append(session_folder)
                if ('pophys' in files or 'ophys' in files)==False and move_files_to_pophys:
                    print('there are too many files and no pophys folder, moving everything')
                    pophys_folder= os.path.join(session_folder,'pophys')
                    print(session_folder)
                    os.mkdir(pophys_folder)
                    for file in files:
                        if '.np' not in file and '.' in file:
                            shutil.move(os.path.join(session_folder,file), 
                                        os.path.join(pophys_folder,file))
                            #%
                else:
                    print('pophys already present, skipping')
                    continue
            if 'session.json' in files:
                print('session.json found, skipping {}'.format(session))
                continue
                #print('NOT SKIPPING')
            
            # create staging folders
            session_folder = os.path.join(dataDir,mouse,session)
            if session_folder in long_behavior_extraction or session_folder in no_behavior_extraction or session_folder in session_json_problem:
                print('skipping because previously identified problem')
                continue
            print('starting {}'.format(session_folder))
            tiff_path = os.path.join(dataDir,mouse,session,'pophys')
            behavior_folder_staging = os.path.join(dataDir,mouse,session,'behavior')
            behavior_video_folder_staging = os.path.join(dataDir,mouse,session,'behavior_video')
            Path(behavior_folder_staging).mkdir(parents=True, exist_ok=True)                                    
            Path(behavior_video_folder_staging).mkdir(parents=True, exist_ok=True)       
            if extract_behavior :
                
                
                
                cmd = (
                    'bash -c "source ~/anaconda3/etc/profile.d/conda.sh && '
                    'conda activate bci_with_suite2p && '
                    'python -u /home/rozmar/Scripts/AIND_Bergamo_upload_tools/export_behavior.py {} {} {}"'
                ).format(mouse, tiff_path, behavior_folder_staging)
                
                try:
                    proc = subprocess.Popen(
                        cmd,
                        shell=True,
                        preexec_fn=os.setsid,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1  # line-buffered
                    )
                    for line in iter(proc.stdout.readline, ''):
                        print(line, end='')
                    proc.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    print("Timed out — killing process group")
                    os.killpg(proc.pid, signal.SIGTERM)
                    long_behavior_extraction.append(session_folder)
                    continue
                    
                
                
# =============================================================================
#                 try:
#                     results = subprocess.run('bash -c "source ~/anaconda3/etc/profile.d/conda.sh && conda activate bci_with_suite2p && python /home/rozmar/Scripts/AIND_Bergamo_upload_tools/export_behavior.py {} {} {}"'.format(
#                                         mouse,
#                                         tiff_path,
#                                         behavior_folder_staging),
#                             shell=True,
#                             timeout=600  # 10 minutes in seconds
#                         )
#                 except subprocess.TimeoutExpired:
#                     print("Behavior extraction timed out after 10 minutes.")
#                     long_behavior_extraction.append(session_folder)
#                     continue
# =============================================================================
                    

            #%
            if create_rig_json:
                rig_json = bergamo_rig.generate_rig_json()
                
                with open(os.path.join(session_folder,'rig.json'), 'w') as json_file:
                    json_file.write(rig_json)
            

            #%
            #from main_utility import *

            behavior_fname  = f"{session}-bpod_zaber.npy"
            
               
            try:
                behavior_data, hittrials, goodtrials, behavior_task_name, is_side_camera_active, is_bottom_camera_active,starting_lickport_position = prepareSessionJSON(Path(behavior_folder_staging), behavior_fname)
            except:
                print('no-learning session?-skipping this one')
                no_behavior_extraction.append(session_folder)
                continue
                behavior_data, hittrials, goodtrials, behavior_task_name, is_side_camera_active, is_bottom_camera_active,starting_lickport_position = prepareSessionJSON(Path(behavior_folder_staging), behavior_fname,nobehavior=True)# there is probably no behavior
                
                
                    
            if stage_videos:
                print('staging videos')
                try:
                    stagingVideos(behavior_data, behavior_video_folder_staging)
                except:
                    print('staging videos failed')
                    video_staging_failed.append(session_folder)
                    continue
            if create_session_json:
                user_settings = JobSettings(    input_source = Path(tiff_path), #date folder local i.e. Y:/BCI93/101724/pophys
                                                output_directory = Path(session_folder), #staging dir folder scratch  i.e. Y:/BCI93/101724
                                                experimenter_full_name = ['Kayvon Daie','Christina Wang','Bryan MacLennan'],
                                                
                                                subject_id  = str(int(subject_id)),#####
                                                imaging_laser_wavelength = int(920),
                                                fov_imaging_depth = int(125),
                                                fov_targeted_structure = 'MOp', 
                                                notes = 'this session json was automatically batch generated',
                                                session_type = "BCI",
                                                iacuc_protocol = "2109",
                                                rig_id = "442_Bergamo_2p_photostim",
                                                behavior_camera_names = np.asarray(["Side Face Camera","Bottom Face Camera"])[np.asarray([is_side_camera_active,is_bottom_camera_active])].tolist(),
                                                imaging_laser_name = "Chameleon Laser",
                                                photostim_laser_name  = "Monaco Laser",
                                                photostim_laser_wavelength =  1035,
                                                starting_lickport_position = starting_lickport_position,
                                                behavior_task_name = behavior_task_name,
                                                hit_rate_trials_0_10 = np.nanmean(hittrials[goodtrials][:10]),
                                                hit_rate_trials_20_40 = np.nanmean(hittrials[goodtrials][20:40]),
                                                total_hits  = sum(hittrials[goodtrials]),
                                                average_hit_rate = sum(hittrials[goodtrials])/sum(goodtrials),
                                                trial_num = sum(goodtrials))
                etl_job = BergamoEtl(job_settings=user_settings,)
                try:
                    session_metadata = etl_job.run_job()
                except:
                    print('could not generate session json')
                    session_json_problem.append(session_folder)
                    continue
            #%
            #from main_utility import *

            
                    ##
            #%
            createPDFs(Path(session_folder), behavior_data,str(int(subject_id)), session,mouse)
            
            
            
  #%%
pophys_in_files = np.asarray(pophys_in_files)
filenum_in_folder = np.asarray(filenum_in_folder)     
filenum_in_folder[filenum_in_folder>950]=950      
fig = plt.figure()
plt.hist(filenum_in_folder[pophys_in_files],np.arange(0,1000,5),color= 'black',alpha = .5) 
plt.hist(filenum_in_folder[pophys_in_files==False],np.arange(0,1000,5),color= 'red',alpha =.5)
plt.yscale('log')     
plt.vlines(50,0,plt.gca().get_ylim()[1],color='red') 
plt.xlabel('# of files in session folder')
plt.ylabel('# of sessoins')           













            
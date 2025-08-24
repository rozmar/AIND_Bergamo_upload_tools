# Bergamo upload tools

## Install AIND metadata dependencies
```
conda create -n codeocean python=3.11
conda activate codeocean
pip install codeocean aind_data_schema_models
pip install git+https://github.com/AllenNeuralDynamics/aind-data-transfer-service.git
pip install git+https://github.com/AllenNeuralDynamics/aind-codeocean-pipeline-monitor.git
```
maybe
#aind_data_transfer_models, aind_data_transfer_service

## Install Pybpod and scanimage dependencies
go somewhere you want these codes to be
```
git clone https://github.com/rozmar/suite2p.git
cd suite2p
conda env create -f environment.yml
conda activate bci_with_suite2p
pip install -e .
cd ..
git clone https://github.com/kpdaie/BCI_analysis.git
cd BCI_analysis
pip install -e .
```


## Usage

01_batch_stage_Bergamo_sessions.py runs through the sessions saved on VAST, and stages them, copies behavior videos, 
02_batch_upload_Bergamo_sessions.py finds the sessions not on VAST, corrects the ones with missing metadata, uploads them to AWS

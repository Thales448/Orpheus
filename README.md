# Orpheus
Syntx backend is designed for scalability. With multiple image factory environments. We produce top tier contianer images to be deployed in a production Kubernetes Cluster. 
In total 4 images make up the entirity of syntxapp backend. They are:


Alpha
    image: thales884/charts:latest

    The Alpha image is the secure compute core of our quant infrastructure where alpha is generated. Houses in-progress algorithms and prorietary statistical tools. 
    Isolated development pods, and secure access to financial data. It runs Kubernetes-native backtesting, strategy development, and optimization jobs.

Charts
    image: thales884/charts:latest
    
    Composed of >150 functions nessesary to interact with the financial timescale databases. Populate, Retrieve, Delete data from the tables. it is also responsible for streaming  current market data

OjO
    image thales884/OjO:latest

    sidecar responsible for centralized logging. collects, aggregates and fowards loggs based on rules. prunes old low priority logs and writes locally and to a cloud for safety.
    responisble for fowarding warnings to appropriate applications. OjO Ai based pruning and selections

Nexus
    image thales884/nexus:latest 
    
    A java server with the administrative dashboard. Central hub for all other images. Responsible for queing and orchastrating kubernetes jobs as needed. The dashboard controls the infill and outfill of 
    the databases. organizes algorithms their backtest, progression and statistics. interfaces with brokerages to display account information. Houses the server-code development staging area.
    gives overview of Orpheus landscape. 



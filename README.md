# background-check-advsior
# Abstract
Amazon polly turns text into life-like speech. This enables the users to talk naturally 
enabling to build speech enable products. Amazon Polly is amazon’s AI services that 
uses advance deep learning technologies to synthesize speech that sounds like a human
voice. The data from the amazon polly will be sent to API gateways which will be using 
AWS lambada in the backend that queries Amazon athena to get the desired output. To 
query athena we need to migrate the data to S3 datalake. We will be using Amazon 
DMS to migrate data from source database to S3.

# Background
The projects help for reporting of background check orders placed by the clients and also 
helps to query archived data with the help of bot (polly). This reduces the workload on 
the operations team.

# Module Diagram for Background Check Advsior:
![image](https://user-images.githubusercontent.com/99464791/226540859-87f10755-e1f2-47dd-9cfe-ad61174040ef.png)

# Functional Block Diagram for Background-Check Advsior:
![image](https://user-images.githubusercontent.com/99464791/226541137-3e05a533-d052-4ba7-b933-9f4aab8ea379.png)


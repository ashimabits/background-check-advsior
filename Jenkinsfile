pipeline {
    agent {
        label "docker:linux"
    }
    environment {
        app_name = "backgroundcheck"
        bc_account = "149053410276"
        bucket_prefix = "backgroundcheck-build-artifacts"
        python_version = "3.7"
    }
    options {
        disableConcurrentBuilds()
        buildDiscarder logRotator(numToKeepStr: "20")
        timestamps()
        parallelsAlwaysFailFast()
    }
    parameters {
        choice(name: "deploy_to", choices: ["int", "prod"], description: "Deploy to Environment")
        choice(name: "region", choices: ["us-east-1", "us-east-2", "ca-central-1", "eu-central-1", "ap-southeast-2"], description: "Deploy to Region")
    }
    stages {
        stage('Build') {
            agent {
                docker {
                    reuseNode true
                    image "python:${python_version}"
                    args '--entrypoint=""'
                    registryUrl "https://repo.dev.backgroundcheck.com:8083"
                }
            }
            steps {
                sh "rm -rf ./package package.zip"
                sh "mkdir -p ./package"
                sh "cp src/* ./package"
                sh "python3 -m pip install -r requirements.txt -t ./package"
                zip zipFile: "package.zip", archive: false, dir: "package"
            }
        }
        stage('Publish') {
            agent {
                docker {
                    reuseNode true
                    image "amazon/aws-cli"
                    args '--entrypoint=""'
                    registryUrl "https://repo.dev.backgroundcheck.com:8083"
                }
            }
            steps {
                withAWS(role: "publish-artifacts-role", roleAccount: bc_account, region: params.region, duration: 3600, roleSessionName: "lambda-upload-cli") {
                    sh "aws s3 cp package.zip s3://${bucket_prefix}-${params.region}/${app_name}/${BRANCH_NAME}/${GIT_COMMIT}/dms-scaling-util/package.zip"
                }
            }
        }
        stage("Deploy Core") {
            agent {
                docker {
                    reuseNode true
                    image "amazon/aws-cli"
                    args '--entrypoint=""'
                    registryUrl "https://repo.dev.backgroundcheck.com:8083"
                }
            }
            steps {
                script {
                    deploy_kms(bc_account)
                    deploy_raw_bucket(bc_account)
                    deploy_curated_bucket(bc_account)
                    deploy_shared_resources(bc_account)
                    deploy_data_retention_autoscaler(bc_account)
                }
            }
        }
        stage('Deploy DMS') {
            agent {
                docker {
                    reuseNode true
                    image "amazon/aws-cli"
                    args '--entrypoint=""'
                    registryUrl "https://repo.dev.backgroundcheck.com:8083"
                }
            }
            steps {
                script {
                    deploy_source_endpoint(bc_account)        
                    deploy_target_endpoint(bc_account)                   
                    deploy_target_task(bc_account)
                }
            }
        }
    }
}
}


def deploy_kms(def account) {
    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "kms-run-cf") {
        cfnUpdate(
            stack: "kms-shared-key", 
            file: "shared/kms-shared-key.yaml", 
            params: [
                "Environment": "${params.deploy_to}"
            ], 
            tags: [
                "service=${app_name}"
            ], 
            create: "true", 
            enableTerminationProtection: "true", 
            roleArn: "arn:aws:iam::$bc_account:role/cloudformation-runas-role", 
            pollInterval: 10000, 
            timeoutInMinutes: 180
        )
    }
}

def deploy_raw_bucket(def account) {
    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "bucket-run-cf") {
        cfnUpdate(
            stack: "s3-$app_name-raw-bucket", 
            file: "shared/s3-base-template.yaml", 
            params: [
                "BucketType": "raw", 
                "Environment": "${params.deploy_to}"
            ], 
            tags: [
                "service=${app_name}"
            ], 
            create: "true", 
            enableTerminationProtection: "true", 
            roleArn: "arn:aws:iam::$bc_account:role/cloudformation-runas-role", 
            pollInterval: 10000, 
            timeoutInMinutes: 180
        )
    }
}

def deploy_curated_bucket(def account) {
    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "bucket-run-cf") {
        cfnUpdate(
            stack: "s3-$app_name-curated-bucket", 
            file: "shared/s3-base-template.yaml", 
            params: [
                "BucketType": "curated", 
                "Environment": "${params.deploy_to}"
            ], 
            tags: [
                "service=${app_name}"
            ], 
            create: "true", 
            enableTerminationProtection: "true", 
            roleArn: "arn:aws:iam::$bc_account:role/cloudformation-runas-role", 
            pollInterval: 10000, 
            timeoutInMinutes: 180
        )
    }
}

def deploy_shared_resources(def account) {
    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "dms-run-cf") {
        cfnUpdate(
            stack: "dms-shared-resources", 
            file: "shared/dms-shared-resources.yaml", 
            params: [
                "Environment": "${params.deploy_to}"
            ], 
            tags: [
                "service=${app_name}"
            ], 
            create: "true", 
            enableTerminationProtection: "true", 
            roleArn: "arn:aws:iam::$bc_account:role/cloudformation-runas-role", 
            pollInterval: 10000, 
            timeoutInMinutes: 180
        )
    }
}

def deploy_data_retention_autoscaler(def account) {
    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "lambda-run-cf") {
        cfnUpdate(
            stack: "lambda-cdc-stream-data-retention-autoscaler", 
            file: "shared/lambda-kinesis-data-retention-autoscaler.yaml", 
            tags: [
                "service=${app_name}"
            ], 
            create: "true", 
            enableTerminationProtection: "true", 
            roleArn: "arn:aws:iam::$bc_account:role/cloudformation-runas-role", 
            pollInterval: 10000, 
            timeoutInMinutes: 180
        )
    }
}

def deploy_dms_instance(def account, def instance_class, def engine_version) {
    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "dms-run-cf") {
        cfnUpdate(
            stack: "dms-backgroundcheck-instance", 
            file: "shared/dms-instance-template.yaml", 
            params: [
                "SourceName": "backgroundcheck", 
                "InstanceClass": "$instance_class", 
                "EngineVersion": "$engine_version"
            ], 
            tags: [
                "service=${app_name}"
            ], 
            create: "true", 
            enableTerminationProtection: "true", 
            roleArn: "arn:aws:iam::$bc_account:role/cloudformation-runas-role", 
            pollInterval: 10000, 
            timeoutInMinutes: 180
        )
    }
}

def deploy_dms_scaling_util(def account) {
    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "dms-sclaing-util-run-cf") {
        cfnUpdate(
            stack: "lambda-dms-backgroundcheck-instance-scaling", 
            file: "shared/lambda-dms-scaling-template.yaml", 
            params: [
                "ArtifactsBucket": "${bucket_prefix}-${params.region}", 
                "ArtifactsKey": "${app_name}/${BRANCH_NAME}/${GIT_COMMIT}/dms-scaling-util/package.zip", 
                "SourceName": "$id"
            ], 
            tags: [
                "service=${app_name}"
            ], 
            create: "true", 
            enableTerminationProtection: "true", 
            roleArn: "arn:aws:iam::$account:role/cloudformation-runas-role", 
            pollInterval: 10000, 
            timeoutInMinutes: 180
        )
    }
}

def deploy_source_endpoint(def account) {
    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "secrets-run-cf") {
        cfnUpdate(
            stack: "dms-backgroundcheck-source-endpoint", 
            file: "shared/dms-source-endpoint-template.yaml", 
            params: [
                "SourceName": "backgroundcheck", 
                "SourceEngine": "sqlserver", 
                "SourceServer": "backgroundcheck.sqlserver.amazon.com", 
                "SourcePort": "1433", 
                "SourceDatabase": "backgroundcheck"                
            ], 
            tags: [
                "service=${app_name}"
            ], 
            create: "true", 
            enableTerminationProtection: "true", 
            roleArn: "arn:aws:iam::$bc_account:role/cloudformation-runas-role", 
            pollInterval: 10000, 
            timeoutInMinutes: 180
        )
    }
}


def deploy_target_endpoint(def account) {
    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "secrets-run-cf") {
        cfnUpdate(
            stack: "dms-backgroundcheck-source-endpoint", 
            file: "shared/dms-target-endpoint-template.yaml",           
            tags: [
                "service=${app_name}"
            ], 
            create: "true", 
            enableTerminationProtection: "true", 
            roleArn: "arn:aws:iam::$bc_account:role/cloudformation-runas-role", 
            pollInterval: 10000, 
            timeoutInMinutes: 180
        )
    }
}

def deploy_target_task(def account, def id, def source_arn, def target) {
    withAWS(role: "publish-artifacts-role", roleAccount: bc_account, region: params.region, duration: 3600, roleSessionName: "s3-upload-task-mappings") {
        mappings_path = "s3://${bucket_prefix}-${params.region}/${app_name}/${BRANCH_NAME}/${GIT_COMMIT}/dms-task-mappings/${target.task}-mappings.yaml"
        sh "aws s3 cp dms/${params.deploy_to}/${target.task}-mappings.yaml $mappings_path"
    }
     source_arn = get_param(data_account, "/dms/backgroundcheck/source/endpoint/arn")
     target_arn = get_param(data_account, "/dms/backgroundcheck/target/endpoint/arn")

    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "dms-s3-task-run-cf") {
        cfnUpdate(
            stack: "${target.task}", 
            file: "dms/${params.deploy_to}/${target.task}.yaml", 
            params: [    
                "SourceEndpointArn": "$source_arn",
                "TargetEndpointArn": "$TargetEndpointArn",
                "DMSTaskMappings": "$mappings_path", 
                "TaskName": "backgroundcheck-full-load-replication-task"
            ], 
            tags: [
                "service=${app_name}"
            ], 
            create: "true", 
            enableTerminationProtection: "true", 
            roleArn: "arn:aws:iam::$bc_account:role/cloudformation-runas-role", 
            pollInterval: 10000, 
            timeoutInMinutes: 180
        )
    }
}

def get_param(def account, def key) {
    def value = ""
    withAWS(role: "jenkins-deployment-role", roleAccount: "$account", region: "${params.region}", duration: 3600, roleSessionName: "get-param-cli") {
        def stdout = sh (script: "aws ssm get-parameter --name $key || true", returnStdout: true)
        if (stdout ?.trim()) {
            def output = readJSON text: "$stdout", returnPojo: true
            value = output.Parameter.Value
        }
    }
    return value
}
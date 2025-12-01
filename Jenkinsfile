pipeline {
    agent any

    environment {
        DEPLOY_USER = "wissend"
        DEPLOY_SERVER = "20.197.53.155"  // Replace with your server IP
        APP_DIR = "/var/www/nuark-interface"
        SSH_KEY = "github-ssh"  // Jenkins SSH credential ID
    }

    stages {

        stage('Clone Repository') {
            steps {
                git branch: 'main',
                    url: 'git@github.com:venkatesh-wissend/nuark-interface.git'
            }
        }

        stage('Upload Code to Server') {
            steps {
                sshagent([SSH_KEY]) {
                    sh """
                        rsync -avz --delete --exclude 'venv' --exclude '.git' ./ ${DEPLOY_USER}@${DEPLOY_SERVER}:${APP_DIR}/app/
                    """
                }
            }
        }

        stage('Install Python Dependencies') {
            steps {
                sshagent([SSH_KEY]) {
                    sh """
                        ssh ${DEPLOY_USER}@${DEPLOY_SERVER} '
                            cd ${APP_DIR}
                            source venv/bin/activate
                            pip install --upgrade pip
                            pip install -r app/requirements.txt
                        '
                    """
                }
            }
        }

        stage('Run Django Migrations') {
            steps {
                sshagent([SSH_KEY]) {
                    sh """
                        ssh ${DEPLOY_USER}@${DEPLOY_SERVER} '
                            cd ${APP_DIR}/app
                            source ../venv/bin/activate
                            python manage.py migrate --noinput
                        '
                    """
                }
            }
        }

        stage('Collect Static Files') {
            steps {
                sshagent([SSH_KEY]) {
                    sh """
                        ssh ${DEPLOY_USER}@${DEPLOY_SERVER} '
                            cd ${APP_DIR}/app
                            source ../venv/bin/activate
                            python manage.py collectstatic --noinput
                        '
                    """
                }
            }
        }

        stage('Restart Application') {
            steps {
                sshagent([SSH_KEY]) {
                    sh """
                        ssh ${DEPLOY_USER}@${DEPLOY_SERVER} '
                            sudo systemctl daemon-reload
                            sudo systemctl restart nuark.service
                            sudo systemctl status nuark.service
                        '
                    """
                }
            }
        }
    }
}

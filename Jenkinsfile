pipeline {
    agent {
        docker { 
            image 'python:3.11' 
            args '-p 5556:5556'
        }
    }
    environment {
        APP_PORT = '5556'
        GITHUB_REPO = 'https://github.com/Qantrex/DEZSYS_JENKINS_HELLOSPENCER.git'
    }
    stages {
        stage('Pre-Build Cleanup') {
            steps {
                // Kill any existing Flask processes
                sh 'pkill -f "python src/hello.py" || true'
            }
        }
        stage('Checkout') {
            steps {
                cleanWs()
                git branch: 'main', url: "${GITHUB_REPO}"
            }
        }
        stage('Build') {
            steps {
                sh '''
                    python -m pip install --upgrade pip
                    pip install flask
                    pip install requests
                    pip install pytest
                    if [ ! -f count.txt ]; then
                        echo "0" > count.txt
                    fi
                    chmod 666 count.txt
                '''
            }
        }
        stage('Test') {
            steps {
                sh '''
                    # Run the unit tests
                    python -m pytest tests/test_hello.py -v
                '''
            }
        }
        stage('Run') {
            steps {
                sh '''
                    nohup python src/hello.py > app.log 2>&1 &
                    sleep 5
                    curl http://localhost:5556/api/hello
                '''
            }
        }
        stage('Test API') {
            steps {
                sh 'python tests/test_api.py'
            }
        }
    }
    post {
        always {
            // Cleanup: Stop the Flask application
            sh 'pkill -f "python src/hello.py" || true'
        }
    }
}
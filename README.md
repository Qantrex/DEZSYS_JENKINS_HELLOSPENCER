# Project Outline

Eine einfache **Flask-API** (`/api/hello`), die über eine **Jenkins CI/CD-Pipeline**
gebaut, getestet und deployt wird. Die Pipeline läuft in einem Docker-Container und
durchläuft die Schritte **Source → Build → Test → Deployment**.

## Setup

### Jenkins (Docker)

```bash
# Jenkins-Container mit Docker-Anbindung an den Host starten
docker run -u root -d \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:latest

# Initiales Admin-Passwort auslesen (zum Entsperren von Jenkins)
docker exec <jenkins_container_name> cat /var/jenkins_home/secrets/initialAdminPassword
```

Anschließend `http://localhost:8080` öffnen, Jenkins entsperren, die empfohlenen
Plugins sowie **Docker** und **CloudBees Docker Build** installieren und einen
Administrator anlegen.

Falls im Jenkins-Container `docker --version` fehlschlägt, die Docker-CLI nachinstallieren:

```bash
docker exec -it <jenkins_container_name> bash
apt-get update
apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce-cli
```

In Jenkins eine **neue Pipeline** anlegen, als *Definition* „Pipeline script from SCM"
wählen, das GitHub-Repository verlinken und als Script-Path `Jenkinsfile` angeben.

### Anwendung lokal starten (ohne Jenkins)

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Flask-App starten (lauscht auf Port 5556)
python src/hello.py
```

### Stop

```bash
# Anwendung
# Ctrl+C im Terminal das python src/hello.py ausführt
# oder im Container:
pkill -f "python src/hello.py"

# Jenkins-Container stoppen
docker stop <jenkins_container_name>
```

---

## How to Use

### Endpoints

| Method | URL | Beschreibung |
|--------|-----|--------------|
| `GET` | `http://localhost:5556/api/hello` | Gibt „Hello Spencer" zurück und erhöht den Aufruf-Counter |

### Beispiel-Antwort

```json
{
  "message": "Hello Spencer",
  "counter": 28,
  "status": "success"
}
```

### CLI Testing

```bash
# API aufrufen
curl http://localhost:5556/api/hello

# Unit-Tests ausführen (App muss dafür nicht laufen)
python -m pytest tests/test_hello.py -v

# Integrationstest ausführen (App muss auf Port 5556 laufen)
python tests/test_api.py
```

---

## Code Snippets

### 1 – Die Flask-API mit persistentem Counter

```python
# src/hello.py
@app.route('/api/hello', methods=['GET'])
def hello_spencer():
    f = open("count.txt", "r")
    counter = int(f.read())
    f.close()
    counter += 1
    f = open("count.txt", "w")
    f.write(str(counter))
    f.close()
    return jsonify({"message": "Hello Spencer", "counter": counter, "status": "success"})
```

Der Endpoint liest bei jedem Aufruf den aktuellen Zählerstand aus `count.txt`, erhöht
ihn um eins und schreibt ihn wieder zurück – so bleibt die Anzahl der Aufrufe über
Neustarts hinweg erhalten. Die Antwort wird mit `jsonify` als JSON serialisiert.

---

### 2 – Pipeline-Agent als Docker-Container

```groovy
// Jenkinsfile
agent {
    docker {
        image 'python:3.11'
        args '-p 5556:5556'
    }
}
```

Jeder Pipeline-Lauf wird in einem frischen `python:3.11`-Container ausgeführt, sodass
die Build-Umgebung reproduzierbar und vom Jenkins-Host isoliert ist. `args '-p 5556:5556'`
gibt den Flask-Port aus dem Container frei.

---

### 3 – Umgebungsvariablen der Pipeline

```groovy
// Jenkinsfile
environment {
    APP_PORT = '5556'
    GITHUB_REPO = 'https://github.com/ThomasMicheler/DEZSYS_JENKINS_HELLOSPENCER.git'
}
```

Der `environment`-Block definiert globale Variablen, die in allen Stages über
`${APP_PORT}` bzw. `${GITHUB_REPO}` referenziert werden können – das hält die
Konfiguration zentral und vermeidet hartkodierte Werte in den einzelnen Stages.

---

### 4 – Source: Checkout aus GitHub

```groovy
// Jenkinsfile
stage('Checkout') {
    steps {
        cleanWs()
        git branch: 'main', url: "${GITHUB_REPO}"
    }
}
```

`cleanWs()` löscht den Workspace vor dem Checkout, damit keine Artefakte eines
früheren Laufs zurückbleiben. `git` klont anschließend den `main`-Branch des
Repositories – das ist der **Source**-Schritt der Pipeline.

---

### 5 – Build: Abhängigkeiten installieren

```groovy
// Jenkinsfile
stage('Build') {
    steps {
        sh '''
            python -m pip install --upgrade pip
            pip install flask requests pytest
            if [ ! -f count.txt ]; then echo "0" > count.txt; fi
            chmod 666 count.txt
        '''
    }
}
```

Im **Build**-Schritt werden die benötigten Python-Pakete installiert und die
`count.txt` initialisiert, falls sie noch nicht existiert. `chmod 666` stellt
sicher, dass die Datei vom App-Prozess beschreibbar ist.

---

### 6 – Test: Unit-Tests mit pytest

```groovy
// Jenkinsfile
stage('Test') {
    steps {
        sh 'python -m pytest tests/test_hello.py -v'
    }
}
```

```python
# tests/test_hello.py
def test_hello_endpoint_data(self):
    response = self.app.get('/api/hello')
    data = json.loads(response.data.decode())
    self.assertEqual(data['message'], 'Hello Spencer')
    self.assertEqual(data['status'], 'success')
```

Der **Test**-Schritt führt die Unit-Tests aus. Diese verwenden den
`app.test_client()` von Flask, der die API ohne laufenden Server direkt im
Prozess testet – geprüft werden Status-Code (200), Content-Type (JSON) und der
Inhalt der Antwort. Schlägt ein Test fehl, bricht die Pipeline ab.

---

### 7 – Deployment & API-Integrationstest

```groovy
// Jenkinsfile
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
```

Im **Deployment**-Schritt wird die App mit `nohup ... &` im Hintergrund gestartet
und nach kurzer Wartezeit mit `curl` erreicht. Die Stage *Test API* führt
anschließend einen Integrationstest gegen die **tatsächlich laufende** Instanz aus
(`requests.get` auf Port 5556) und prüft auch die Antwortzeit (< 1 Sekunde).

---

### 8 – Post-Aktion: Aufräumen

```groovy
// Jenkinsfile
post {
    always {
        sh 'pkill -f "python src/hello.py" || true'
    }
}
```

Der `post { always { ... } }`-Block läuft unabhängig vom Pipeline-Ergebnis und
beendet den Flask-Prozess. Das `|| true` verhindert, dass die Pipeline scheitert,
falls kein passender Prozess gefunden wird.

---

# Protokoll – CI/CD Pipelines in Jenkins

## Fragen

### Was ist CI/CD und welche Vorteile bietet es?

CI (Continuous Integration) bedeutet, dass Codeänderungen häufig in ein gemeinsames
Repository integriert und automatisch gebaut und getestet werden. CD (Continuous
Delivery/Deployment) erweitert dies um die automatische Auslieferung bzw. das
automatische Deployment der Anwendung. Die Vorteile sind schnelleres Feedback bei
Fehlern, weniger manuelle Arbeit, reproduzierbare Builds und eine höhere Software-
Qualität durch automatisierte Tests bei jedem Commit.

### Was ist Jenkins und wozu dient ein Jenkinsfile?

Jenkins ist ein quelloffener Automatisierungsserver, der als CI/CD-Tool zum
automatischen Bauen, Testen und Deployen von Software dient. Ein `Jenkinsfile`
beschreibt die Pipeline als Code (Pipeline-as-Code) in deklarativer Groovy-Syntax
und wird zusammen mit dem Quellcode im Repository versioniert. So ist die gesamte
CI/CD-Konfiguration nachvollziehbar, versioniert und mit dem Projekt verknüpft.

### Welche Schritte (Stages) umfasst die Pipeline in diesem Projekt?

| Stage | Aufgabe |
|---|---|
| **Checkout** (Source) | Workspace bereinigen und Code aus GitHub klonen |
| **Build** | Python-Abhängigkeiten installieren, `count.txt` initialisieren |
| **Test** | Unit-Tests mit pytest ausführen |
| **Run** (Deployment) | Flask-App im Hintergrund starten und per curl prüfen |
| **Test API** | Integrationstest gegen die laufende Instanz |

### Welche Rolle spielt Docker in dieser Pipeline?

Docker wird auf zwei Ebenen eingesetzt: Erstens läuft die Pipeline selbst in einem
`python:3.11`-Container als Agent, wodurch eine isolierte und reproduzierbare
Build-Umgebung entsteht. Zweitens ermöglicht das Einbinden des Docker-Sockets
(`-v /var/run/docker.sock:/var/run/docker.sock`) Jenkins, Container auf dem
Host-Docker-Daemon zu starten. Das mitgelieferte `Dockerfile` erlaubt zusätzlich,
die Anwendung selbst als eigenständiges Image zu paketieren.

### Wie kann eine Pipeline automatisch durch einen Commit gestartet werden?

Über einen **Webhook**: In den GitHub-Repository-Einstellungen wird unter
*Settings → Webhooks* die Jenkins-URL (`http://<jenkins-host>:8080/github-webhook/`)
eingetragen. In Jenkins wird im Pipeline-Job die Option *„GitHub hook trigger for
GITScm polling"* aktiviert. Bei jedem Push sendet GitHub dann ein Event an Jenkins,
das die Pipeline automatisch auslöst. Alternativ kann *Poll SCM* in regelmäßigen
Abständen das Repository auf Änderungen prüfen.

### Worin unterscheiden sich Unit-Test und Integrationstest in diesem Projekt?

Der Unit-Test (`test_hello.py`) nutzt den Flask-`test_client()` und prüft die API
direkt im Prozess, ohne dass ein Server laufen muss – er testet die Logik isoliert.
Der Integrationstest (`test_api.py`) sendet dagegen echte HTTP-Requests mit der
`requests`-Bibliothek an die **laufende** Anwendung auf Port 5556 und prüft so das
Zusammenspiel von Server, Netzwerk und Endpoint inklusive Antwortzeit.

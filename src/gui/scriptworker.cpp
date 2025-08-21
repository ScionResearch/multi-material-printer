#include "scriptworker.h"
#include <QDebug>
#include <QTimer>

ScriptWorker::ScriptWorker(QObject *parent)
    : QObject(parent), currentProcess(nullptr), isRunning(false), consecutiveFailures(0)
{
}

ScriptWorker::~ScriptWorker()
{
    if (currentProcess && currentProcess->state() != QProcess::NotRunning)
    {
        currentProcess->terminate();
        if (!currentProcess->waitForFinished(3000))
        {
            currentProcess->kill();
            currentProcess->waitForFinished(1000);
        }
    }
    
    if (currentProcess)
    {
        delete currentProcess;
        currentProcess = nullptr;
    }
}

void ScriptWorker::executeScript(const QString &scriptPath, const QStringList &arguments)
{
    if (isRunning)
    {
        emit scriptError("Another script is already running");
        return;
    }

    if (!currentProcess)
    {
        currentProcess = new QProcess(this);
        connect(currentProcess, &QProcess::readyReadStandardOutput,
                this, &ScriptWorker::handleProcessOutput);
        connect(currentProcess, &QProcess::readyReadStandardError,
                this, &ScriptWorker::handleProcessError);
        connect(currentProcess, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
                this, &ScriptWorker::handleProcessFinished);
    }

    isRunning = true;
    emit operationStarted();

    QString pythonInterpreter = "python3";
#ifdef Q_OS_WIN
    pythonInterpreter = "python.exe";
#endif

    QStringList fullArguments;
    fullArguments << scriptPath << arguments;

    currentProcess->start(pythonInterpreter, fullArguments);
}

void ScriptWorker::executeCommand(const QString &scriptPath, const QString &printerIP, const QString &command)
{
    QStringList arguments;
    arguments << "-i" << printerIP << "-c" << command;
    executeScript(scriptPath, arguments);
}

void ScriptWorker::checkStatus(const QString &scriptPath, const QString &printerIP)
{
    if (isRunning)
    {
        emit statusResult("Status check already in progress", false);
        return;
    }

    if (!currentProcess)
    {
        currentProcess = new QProcess(this);
        connect(currentProcess, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
                this, [this](int /*exitCode*/, QProcess::ExitStatus exitStatus) {
                    QString output = currentProcess->readAllStandardOutput();
                    QString error = currentProcess->readAllStandardError();
                    
                    if (exitStatus == QProcess::NormalExit && error.isEmpty())
                    {
                        consecutiveFailures = 0; // Reset failure counter on success
                        analyzeStatusOutput(output);
                        emit statusResult(output, true);
                    }
                    else
                    {
                        consecutiveFailures++;
                        analyzeErrorOutput(error);
                        
                        QString errorMsg = error.isEmpty() ? "Connection timeout or unknown error" : error;
                        emit statusResult(errorMsg, false);
                        
                        // Emit connection lost after multiple consecutive failures
                        if (consecutiveFailures >= 3)
                        {
                            emit connectionLost();
                        }
                    }
                    
                    isRunning = false;
                });
    }

    isRunning = true;

    QString pythonInterpreter = "python3";
#ifdef Q_OS_WIN
    pythonInterpreter = "python.exe";
#endif

    QStringList arguments;
    arguments << scriptPath << "-i" << printerIP << "-c" << "getstatus";

    // Set timeout for the process
    currentProcess->start(pythonInterpreter, arguments);
    
    // Add a timeout timer
    QTimer::singleShot(10000, this, [this]() {
        if (currentProcess && currentProcess->state() != QProcess::NotRunning)
        {
            currentProcess->terminate();
            emit statusResult("Operation timed out", false);
            consecutiveFailures++;
        }
    });
}

void ScriptWorker::stopCurrentProcess()
{
    if (currentProcess && currentProcess->state() != QProcess::NotRunning)
    {
        currentProcess->terminate();
        if (!currentProcess->waitForFinished(3000))
        {
            currentProcess->kill();
        }
    }
    isRunning = false;
}

void ScriptWorker::handleProcessOutput()
{
    if (currentProcess)
    {
        QByteArray data = currentProcess->readAllStandardOutput();
        emit scriptOutput(QString::fromUtf8(data));
    }
}

void ScriptWorker::handleProcessError()
{
    if (currentProcess)
    {
        QByteArray data = currentProcess->readAllStandardError();
        emit scriptError(QString::fromUtf8(data));
    }
}

void ScriptWorker::handleProcessFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    isRunning = false;
    emit scriptFinished(exitCode, exitStatus);
}

void ScriptWorker::analyzeErrorOutput(const QString &error)
{
    QString lowerError = error.toLower();
    
    // Check for connection-related errors
    if (lowerError.contains("connection") && (lowerError.contains("refused") || lowerError.contains("timeout")))
    {
        emit connectionLost();
    }
    else if (lowerError.contains("network") && lowerError.contains("unreachable"))
    {
        emit connectionLost();
    }
    // Check for hardware-related errors
    else if (lowerError.contains("pump") && lowerError.contains("failure"))
    {
        emit hardwareError("Pump failure detected");
    }
    else if (lowerError.contains("motor") && (lowerError.contains("error") || lowerError.contains("fault")))
    {
        emit hardwareError("Motor error detected");
    }
    else if (lowerError.contains("sensor") && (lowerError.contains("error") || lowerError.contains("fault")))
    {
        emit hardwareError("Sensor error detected");
    }
    else if (lowerError.contains("temperature") && lowerError.contains("error"))
    {
        emit hardwareError("Temperature sensor error");
    }
}

void ScriptWorker::analyzeStatusOutput(const QString &output)
{
    QString lowerOutput = output.toLower();
    
    // Check for error conditions in status output
    if (lowerOutput.contains("error") || lowerOutput.contains("fault"))
    {
        if (lowerOutput.contains("pump"))
        {
            emit hardwareError("Pump error reported in status");
        }
        else if (lowerOutput.contains("motor"))
        {
            emit hardwareError("Motor error reported in status");
        }
        else
        {
            emit hardwareError("Unknown hardware error reported in status");
        }
    }
    
    // Check for warning conditions
    if (lowerOutput.contains("warning") || lowerOutput.contains("overheating"))
    {
        emit hardwareError("Warning condition detected: " + output.mid(0, 100)); // Limit message length
    }
}
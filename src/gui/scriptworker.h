#ifndef SCRIPTWORKER_H
#define SCRIPTWORKER_H

#include <QObject>
#include <QProcess>
#include <QThread>
#include <QTimer>

class ScriptWorker : public QObject
{
    Q_OBJECT

public:
    explicit ScriptWorker(QObject *parent = nullptr);
    ~ScriptWorker();

public slots:
    void executeScript(const QString &scriptPath, const QStringList &arguments);
    void executeCommand(const QString &scriptPath, const QString &printerIP, const QString &command);
    void checkStatus(const QString &scriptPath, const QString &printerIP);
    void stopCurrentProcess();

signals:
    void scriptOutput(const QString &output);
    void scriptError(const QString &error);
    void scriptFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void statusResult(const QString &statusText, bool success);
    void operationStarted();
    void connectionLost();
    void hardwareError(const QString &errorDescription);

private slots:
    void handleProcessOutput();
    void handleProcessError();
    void handleProcessFinished(int exitCode, QProcess::ExitStatus exitStatus);

private:
    void analyzeErrorOutput(const QString &error);
    void analyzeStatusOutput(const QString &output);
    
    QProcess *currentProcess;
    bool isRunning;
    int consecutiveFailures;
};

#endif // SCRIPTWORKER_H
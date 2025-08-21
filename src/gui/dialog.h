#ifndef DIALOG_H
#define DIALOG_H

#include <QDialog>
#include <QProcess>
#include <Qt3DExtras/Qt3DWindow>
#include <Qt3DRender/QCamera>
#include <Qt3DRender/QMesh>
#include <Qt3DExtras/QOrbitCameraController>
#include <QListWidget>
#include <QTableWidget>
#include <QComboBox>
#include <QSpinBox>
#include <QThread>
#include <QProgressBar>
#include "scriptworker.h"


namespace Ui {
class Dialog;
}

class QNetworkConfigurationManager; // Forward declaration
class QProcess; // Forward declaration

class Dialog : public QDialog
{
    Q_OBJECT

public:
    explicit Dialog(QWidget *parent = nullptr);
    ~Dialog();

private slots:

    void on_lineEdit_returnPressed();

    void on_submitline_clicked();

    ///void checkConnectionStatus();
    void showEvent(QShowEvent* event);
    void updateConnectionStatus();

    void on_startPr_clicked();

    void on_stopPr_clicked();

    void on_checkstatus_clicked();

    void on_pausePr_clicked();

    void on_resumePr_clicked();

    void on_manualrun_clicked();


    //void on_connectbutton_clicked();




    void on_getFiles_clicked();

    void on_stopMr_clicked();

    void on_stopMM_clicked();

    void on_addRecipeRow_clicked();

    void on_removeRecipeRow_clicked();

    void on_loadRecipe_clicked();

    void on_toggleAutoUpdate_clicked();

    void on_startMultiMaterialPrint_clicked();

private slots:
    void handleScriptOutput(const QString &output);
    void handleScriptError(const QString &error);
    void handleScriptFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void handleStatusResult(const QString &statusText, bool success);
    void handleOperationStarted();
    void handleConnectionLost();
    void handleHardwareError(const QString &errorDescription);
    void setButtonStates(bool enabled);

private:
    Ui::Dialog *ui;
     QString runPythonScript(const QString &scriptPath);
     QString handlePythonFunction();
     QString getFileSelection();
     void onPrintFileclicked(QListWidgetItem *item);
     void checkConnectionStatus();
     void setupRecipeTable();
     void setupTooltips();
     void setupKeyboardShortcuts();
     void setupClearOutputButton();
     void updateUtilityStatus(const QString &message);
     void addRecipeTableRow(int layerNum = 1, const QString &material = "A");
     QString generateRecipeString();
     void updateStatusDisplay();
     void parseStatusResponse(const QString &response);
     void updateConnectionStatus(bool connected);
     QString getNextMaterialChange();
     bool validatePrintSetup();
     bool validateRecipe();
     bool validateConnection();
     bool validateMotorControlInput(const QString &input);
     void clearRecipeTableWidgets();
     void optimizeForSmallScreen();
     QProcess *pythonProcess = nullptr; // Pointer to the Python script process
     QProcess *pythonFunction = nullptr;
     QProcess *WiFiFunction;
     QTimer *timer;
     QTimer *statusUpdateTimer;
     bool autoUpdateEnabled;
     ScriptWorker *scriptWorker;
     QThread *workerThread;
};

#endif // DIALOG_H

#ifndef DIALOG_H
#define DIALOG_H

#include <QDialog>
#include <QProcess>
#include <Qt3DExtras/Qt3DWindow>
#include <Qt3DRender/QCamera>
#include <Qt3DRender/QMesh>
#include <Qt3DExtras/QOrbitCameraController>
#include <QListWidget>


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


private:
    Ui::Dialog *ui;
     QString runPythonScript(const QString &scriptPath);
     QString handlePythonFunction();
     QString getFileSelection();
     void onPrintFileclicked(QListWidgetItem *item);
     void checkConnectionStatus();
     QProcess *pythonProcess = nullptr; // Pointer to the Python script process
     QProcess *pythonFunction = nullptr;
     QProcess *WiFiFunction;
     QTimer *timer;
};

#endif // DIALOG_H

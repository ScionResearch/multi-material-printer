#include "dialog.h"
#include "ui_dialog.h"
#include <QCoreApplication>
#include <QFile>
#include <QTextStream>
#include <QMessageBox>
#include <QProcess>
#include <QDir>
#include <QTimer>
#include <QNetworkInterface>
#include <QNetworkAddressEntry>
#include <QFileDialog>
#include <QProcessEnvironment>
#include <QInputDialog>
#include <QStringList>

Dialog::Dialog(QWidget *parent)
    : QDialog(parent), ui(new Ui::Dialog), pythonProcess(nullptr)
{

    ui->setupUi(this);
    // Connect button signal to slot
}

Dialog::~Dialog()
{
    delete ui;
}

void Dialog::on_submitline_clicked()
{
    QString text = ui->lineEdit->text();  // Get the text from the line edit
    QString programDir = QCoreApplication::applicationDirPath();  // Get the program's directory path
    QString filename = programDir + "/output.txt";  // Specify the full path for the .txt file

    QFile file(filename);
    if (file.open(QIODevice::WriteOnly | QIODevice::Text))
    {
        QTextStream stream(&file);
        stream << text;  // Write the text to the file
        file.close();

        // Show a confirmation message
        QMessageBox::StandardButton reply = QMessageBox::question(this, "File Created", "The file has been created successfully. Do you want to open the folder?", QMessageBox::Yes | QMessageBox::No);
        if (reply == QMessageBox::Yes)
        {
            // Open the folder where the file was created
#ifdef Q_OS_WIN
            QProcess::startDetached("explorer.exe", {"/select,", QDir::toNativeSeparators(filename)});
#elif defined(Q_OS_LINUX)
            QProcess::startDetached("xdg-open", {programDir});
#endif
        }
    }
    else
    {
        QMessageBox::critical(this, "Error", "Failed to create the file.");
    }
}

void Dialog::on_lineEdit_returnPressed()
{
    // Empty function, remove if not needed
}

void checkConnectionStatus()
    {

}

void Dialog::showEvent(QShowEvent* event)
{
    QDialog::showEvent(event);

    // Start a timer to periodically check the connection status
    QTimer* timer = new QTimer(this);
    connect(timer, &QTimer::timeout, this, &Dialog::updateConnectionStatus);
    timer->start(5000);  // Adjust the interval (in milliseconds) according to your needs
}

void Dialog::updateConnectionStatus()
{

}

void Dialog::on_startPr_clicked()
{
    QString pythonScriptPath = getFileSelection();

    if (!pythonScriptPath.isEmpty())
    {
        if (!pythonProcess)
        {
            ui->textBrowser->append("Started Print...");
            pythonProcess = new QProcess(this);
            connect(pythonProcess, &QProcess::readyReadStandardOutput, this, [this]() {
            QString output = pythonProcess->readAllStandardOutput();
            //QMessageBox::information(this, "Python Script Output", output);
            ui->textBrowser->append(output);
            });
        }
        else
        {
            pythonProcess->terminate();
            pythonProcess->waitForFinished();
        }
    pythonProcess->start("python3", QStringList() << pythonScriptPath);
    }

}


QString Dialog::runPythonScript(const QString &scriptPath)
{
    QProcess process;
    QString pythonInterpreter = "python3"; // Default Python interpreter command
#ifdef Q_OS_WIN
    pythonInterpreter = "python.exe"; // Windows Python interpreter command
#endif

    QStringList arguments;
    arguments << scriptPath;

    process.start(pythonInterpreter, arguments);
    process.waitForFinished(-1);

    QByteArray output = process.readAllStandardOutput();
    return QString(output);
}

QString Dialog::getFileSelection()
{
    QFileDialog dialog(this);
       dialog.setWindowTitle("Select Python Script");
       dialog.setFileMode(QFileDialog::ExistingFile);
       dialog.setNameFilter("Python Scripts (*.py)");

       QString defaultPath = QCoreApplication::applicationDirPath();
       dialog.setDirectory(defaultPath);

       if (dialog.exec() == QFileDialog::Accepted)
       {
           QStringList selectedFiles = dialog.selectedFiles();
           if (!selectedFiles.isEmpty())
               return selectedFiles.first();
       }

       return QString();
}

void Dialog::on_stopPr_clicked()
{
    QString pythonCommand = "python3 /home/pidlp/pidlp/dev/scripts/newmonox.py -i 192.168.4.2 -c gostop,end";  // Replace with your desired Python command
    ui->textBrowser->append(pythonCommand);

    QProcess process;
    process.start(pythonCommand);
    process.waitForFinished();

    QByteArray output = process.readAllStandardOutput();
    QByteArray error = process.readAllStandardError();

    if (error.isEmpty())
    {
       QString result = QString::fromUtf8(output);
       QMessageBox::information(this, "Python Command Result", result);
       ui->textBrowser->append(result);
    }
    else
    {
       QString errorMessage = QString::fromUtf8(error);
       QMessageBox::critical(this, "Python Command Error", errorMessage);
       ui->textBrowser->append(errorMessage);
   }

}

void Dialog::on_checkstatus_clicked()
{
    QString pythonCommand = "python3 /home/pidlp/pidlp/dev/scripts/newmonox.py -i 192.168.4.2 -c getstatus";  // Replace with your desired Python command
    ui->textBrowser->append(pythonCommand);

    QProcess process;
    process.start(pythonCommand);
    process.waitForFinished();

    QByteArray output = process.readAllStandardOutput();
    QByteArray error = process.readAllStandardError();

    if (error.isEmpty())
    {
       QString result = QString::fromUtf8(output);
      // QMessageBox::information(this, "Python Command Result", result);
       ui->textBrowser->append("\n******STATUS******\n");
       ui->textBrowser->append(result);
       ui->textBrowser->append("******END STATUS******");
       ui->statusLabel->setText("Connected...");
    }
    else
    {
       QString errorMessage = QString::fromUtf8(error);
       //QMessageBox::critical(this, "Python Command Error", errorMessage);
       ui->textBrowser->append(errorMessage);
       ui->statusLabel->setText("Disconnected...");
   }
}

void Dialog::on_pausePr_clicked()
{
    QString pythonCommand = "python3 /home/pidlp/pidlp/dev/scripts/newmonox.py -i 192.168.4.2 -c gopause";  // Replace with your desired Python command
    ui->textBrowser->append(pythonCommand);

    QProcess process;
    process.start(pythonCommand);
    process.waitForFinished();

    QByteArray output = process.readAllStandardOutput();
    QByteArray error = process.readAllStandardError();

    if (error.isEmpty())
    {
       QString result = QString::fromUtf8(output);
       QMessageBox::information(this, "Python Command Result", result);
       ui->textBrowser->append("\n******PAUSE******\n");
       ui->textBrowser->append(result);
       ui->textBrowser->append("\n******END PAUSE******");
    }
    else
    {
       QString errorMessage = QString::fromUtf8(error);
       QMessageBox::critical(this, "Python Command Error", errorMessage);
       ui->textBrowser->append(errorMessage);
   }
}

void Dialog::on_resumePr_clicked()
{
    QString pythonCommand = "python3 /home/pidlp/pidlp/dev/scripts/newmonox.py -i 192.168.4.2 -c goresume";  // Replace with your desired Python command
    ui->textBrowser->append(pythonCommand);

    QProcess process;
    process.start(pythonCommand);
    process.waitForFinished();

    QByteArray output = process.readAllStandardOutput();
    QByteArray error = process.readAllStandardError();

    if (error.isEmpty())
    {
       QString result = QString::fromUtf8(output);
       QMessageBox::information(this, "Python Command Result", result);
       ui->textBrowser->append("\n******RESUME******\n");
       ui->textBrowser->append(result);
       ui->textBrowser->append("\n******END RESUME******");
    }
    else
    {
       QString errorMessage = QString::fromUtf8(error);
       QMessageBox::critical(this, "Python Command Error", errorMessage);
       ui->textBrowser->append(errorMessage);
   }
}

void Dialog::on_manualrun_clicked()
{
    QString scriptPath = "/home/pidlp/pidlp/dev/scripts/photonmmu_pump.py";
    QString functionName = "run_stepper";

    // Set the input text from the line edit
    QString inputText = ui->motor_settings->text();
    ui->textBrowser->append(inputText);

    // Split the input using a comma as the delimiter
    QStringList inputValues = inputText.split(",");

if (inputValues.size() != 3)
    {
        // Incorrect Input format and display an error
        QMessageBox::critical(this, "Error", "Invalid input format. Expected format: A, F in Motor Control line");
        return;
    }
    QString argumentMotor = inputValues[0].trimmed();
    QString argumentDirection = inputValues[1].trimmed();
    QString argumentTiming = inputValues[2].trimmed();
    int intargumentTiming = argumentTiming.toInt();
    QString terminalCommand = QString("python3 -c \"import sys; sys.path.append('%1'); from %2 import %3; %3('%4', '%5', %6)\"")
        .arg(QFileInfo(scriptPath).absolutePath())
        .arg(QFileInfo(scriptPath).baseName())
        .arg(functionName)
        .arg(argumentMotor)
        .arg(argumentDirection)
        .arg(intargumentTiming);
    QString A = argumentMotor;
    QString B = argumentDirection;
    QString C = argumentTiming;
    ui->textBrowser->append(terminalCommand);
    ui->textBrowser->append(A);
    ui->textBrowser->append(B);
    ui->textBrowser->append(C);
    //pythonFunction = new QProcess;

    if (!pythonFunction)
    {
        ui->textBrowser->append("Started Motor...");
        pythonFunction = new QProcess(this);
        connect(pythonFunction, &QProcess::readyReadStandardOutput, this, [this]()   {
                QString output = QString::fromUtf8(pythonFunction->readAllStandardOutput());
                QMessageBox::information(this, "Motor Output", output);
                ui->textBrowser->append("\n******MOTOR RUNNING******\n");
                ui->textBrowser->append(output);
                ui->textBrowser->append("\n******END MOTOR RUNNING******");
                });
    }
    else
    {
        pythonFunction->terminate();
        pythonFunction->waitForFinished();
    }

    pythonFunction->start("/bin/bash", QStringList() << "-c" <<terminalCommand);



    //QProcess process(this);



    //QString output = process.readAllStandardOutput();
    //QString error = process.readAllStandardError();

    //ui->textBrowser->setText(output);
   // QMessageBox::information(this, "Output", output);
}


void Dialog::on_getFiles_clicked()
{
    QString pythonCommand = "python3 /home/pidlp/pidlp/dev/scripts/newmonox.py -i 192.168.4.2 -c getfiles";  // Replace with your desired Python command
    ui->textBrowser->append(pythonCommand);
    ui->filesWidget->clear();
    QProcess process;
    process.start(pythonCommand);
    process.waitForFinished();

    QByteArray output = process.readAllStandardOutput();
    QByteArray error = process.readAllStandardError();

    if (error.isEmpty())
    {
       QString result = QString::fromUtf8(output);
       QMessageBox::information(this, "Python Command Result", result);
       ui->textBrowser->append("\n******FILES******\n");
       ui->textBrowser->append(result);
       ui->textBrowser->append("\n******END FILES******");
       QString resultString(result);
       QStringList resultlist =
               resultString.split('\n');

       ui->filesWidget->addItems(resultlist);

    }
    else
    {
       ui->filesWidget->clear();
       QString errorMessage = QString::fromUtf8(error);
       QMessageBox::critical(this, "Python Command Error", errorMessage);
       ui->textBrowser->append(errorMessage);
   }
    connect(ui->filesWidget,&QListWidget::itemClicked, this, &Dialog::onPrintFileclicked);
}

void Dialog::onPrintFileclicked(QListWidgetItem *item)
{
    QString internalname = "";
    QString externalname = "";
    QString pythonCommand = "python3 /home/pidlp/pidlp/dev/scripts/newmonox.py -i 192.168.4.2 -c goprint,";
    QMessageBox::StandardButton reply = QMessageBox::question(this,"Confirmation", "Are you sure you want to print this file?", QMessageBox::Yes | QMessageBox::No);
    if (reply == QMessageBox::Yes)
    {
        QString itemText = item->text();
        QStringList parts = itemText.split(':');
        if (parts.size() == 2)
        {
            QString internalname = parts[0];
            QString externalname = parts[1];
            ui->textBrowser->append(internalname);
            pythonCommand.append(internalname);
            pythonCommand+=",end";
            ui->textBrowser->append(pythonCommand);
        }
    }
    else
    {
    }


    QProcess process;
    process.start(pythonCommand);
    process.waitForFinished();

    QByteArray output = process.readAllStandardOutput();
    QByteArray error = process.readAllStandardError();

    if (error.isEmpty())
    {
       QString result = QString::fromUtf8(output);
       //QMessageBox::information(this, "Python Command Result", result);
       ui->textBrowser->append("\n******PRINTING FILE******\n");
       ui->textBrowser->append(result);
       ui->textBrowser->append("\n******END PRINTING FILE******");
    }
    else
    {
       QString errorMessage = QString::fromUtf8(error);
       //QMessageBox::critical(this, "Python Command Error", errorMessage);
       ui->textBrowser->append(errorMessage);
   }
}

void Dialog::on_stopMr_clicked()
{
    if (pythonFunction && pythonFunction->state() != QProcess::NotRunning)
    {
        ui->textBrowser->append("Stopped Motor...");
        pythonFunction->terminate();
        pythonFunction->waitForFinished();
        pythonFunction->deleteLater();
        pythonFunction = nullptr;
    }
}

void Dialog::on_stopMM_clicked()
{
    if (pythonProcess && pythonProcess->state() != QProcess::NotRunning)
    {
        ui->textBrowser->append("Stopped MM...");
        pythonProcess->terminate();
        pythonProcess->waitForFinished();
        pythonProcess->deleteLater();
        pythonProcess = nullptr;
    }
}

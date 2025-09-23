#include "dialog.h"
#include "ui_dialog.h"
#include "configmanager.h"
#include <QCoreApplication>
#include <QFile>
#include <QTextStream>
#include <QMessageBox>
#include <QProcess>
#include <QDir>
#include <QTimer>
#include <QFileInfo>
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
    QString filename = ConfigManager::instance().getRecipePath();  // Use config manager for recipe path

    QFile file(filename);
    if (file.open(QIODevice::WriteOnly | QIODevice::Text))
    {
        QTextStream stream(&file);
        stream << text;  // Write the text to the file
        file.close();

        // Show a confirmation message
        QMessageBox::StandardButton reply = QMessageBox::question(this, "Recipe Saved", "The recipe has been saved successfully. Do you want to open the config folder?", QMessageBox::Yes | QMessageBox::No);
        if (reply == QMessageBox::Yes)
        {
            // Open the folder where the file was created
            QString configDir = ConfigManager::instance().getConfigPath();
#ifdef Q_OS_WIN
            QProcess::startDetached("explorer.exe", {"/select,", QDir::toNativeSeparators(filename)});
#elif defined(Q_OS_LINUX)
            QProcess::startDetached("xdg-open", {configDir});
#endif
        }
    }
    else
    {
        QMessageBox::critical(this, "Error", "Failed to create the recipe file.");
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
    QString scriptPath = ConfigManager::instance().getScriptPath("printer_comms.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString pythonCommand = QString("python3 -c \"import sys; sys.path.append('%1'); from printer_comms import stop_print; stop_print('%2')\"").arg(QFileInfo(scriptPath).absolutePath(), printerIP);
    ui->textBrowser->append(pythonCommand);

    QProcess process;
    process.start("python3", QStringList() << "-c" << QString("import sys; sys.path.append('%1'); from printer_comms import stop_print; stop_print('%2')").arg(QFileInfo(scriptPath).absolutePath(), printerIP));
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
    QString scriptPath = ConfigManager::instance().getScriptPath("printer_comms.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString pythonCommand = QString("python3 -c \"import sys; sys.path.append('%1'); from printer_comms import get_status; print(get_status('%2'))\"").arg(QFileInfo(scriptPath).absolutePath(), printerIP);
    ui->textBrowser->append(pythonCommand);

    QProcess process;
    process.start("python3", QStringList() << "-c" << QString("import sys; sys.path.append('%1'); from printer_comms import get_status; print(get_status('%2'))").arg(QFileInfo(scriptPath).absolutePath(), printerIP));
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
    QString scriptPath = ConfigManager::instance().getScriptPath("printer_comms.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString pythonCommand = QString("python3 -c \"import sys; sys.path.append('%1'); from printer_comms import pause_print; pause_print('%2')\"").arg(QFileInfo(scriptPath).absolutePath(), printerIP);
    ui->textBrowser->append(pythonCommand);

    QProcess process;
    process.start("python3", QStringList() << "-c" << QString("import sys; sys.path.append('%1'); from printer_comms import pause_print; pause_print('%2')").arg(QFileInfo(scriptPath).absolutePath(), printerIP));
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
    QString scriptPath = ConfigManager::instance().getScriptPath("printer_comms.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString pythonCommand = QString("python3 -c \"import sys; sys.path.append('%1'); from printer_comms import resume_print; resume_print('%2')\"").arg(QFileInfo(scriptPath).absolutePath(), printerIP);
    ui->textBrowser->append(pythonCommand);

    QProcess process;
    process.start("python3", QStringList() << "-c" << QString("import sys; sys.path.append('%1'); from printer_comms import resume_print; resume_print('%2')").arg(QFileInfo(scriptPath).absolutePath(), printerIP));
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
    QString scriptPath = ConfigManager::instance().getScriptPath("photonmmu_pump.py");
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
    QString scriptPath = ConfigManager::instance().getScriptPath("printer_comms.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString pythonCommand = QString("python3 -c \"import sys; sys.path.append('%1'); from printer_comms import get_files; print(get_files('%2'))\"").arg(QFileInfo(scriptPath).absolutePath(), printerIP);
    ui->textBrowser->append(pythonCommand);
    ui->filesWidget->clear();

    QProcess process;
    process.start("python3", QStringList() << "-c" << QString("import sys; sys.path.append('%1'); from printer_comms import get_files; print(get_files('%2'))").arg(QFileInfo(scriptPath).absolutePath(), printerIP));
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
    QString scriptPath = ConfigManager::instance().getScriptPath("printer_comms.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString internalname = "";
    QString externalname = "";
    QString pythonCommand = QString("python3 -c \"import sys; sys.path.append('%1'); from printer_comms import start_print; start_print('%3', '%2')\"").arg(QFileInfo(scriptPath).absolutePath(), printerIP);
    QMessageBox::StandardButton reply = QMessageBox::question(this,"Confirmation", "Are you sure you want to print this file?", QMessageBox::Yes | QMessageBox::No);
    if (reply == QMessageBox::Yes)
    {
        QString itemText = item->text();
        QStringList parts = itemText.split(':');
        if (parts.size() == 2)
        {
            internalname = parts[0];
            externalname = parts[1];
            ui->textBrowser->append(internalname);
            pythonCommand = pythonCommand.arg(internalname);
            ui->textBrowser->append(pythonCommand);
        }
    }
    else
    {
        return; // User cancelled
    }


    QProcess process;
    process.start("python3", QStringList() << "-c" << QString("import sys; sys.path.append('%1'); from printer_comms import start_print; start_print('%2', '%3')").arg(QFileInfo(scriptPath).absolutePath(), internalname, printerIP));
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

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
    : QDialog(parent), ui(new Ui::Dialog), pythonProcess(nullptr), statusTimer(nullptr)
{
    ui->setupUi(this);

    // Initialize status polling timer
    statusTimer = new QTimer(this);
    connect(statusTimer, &QTimer::timeout, this, &Dialog::autoStatusUpdate);
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

void Dialog::autoStatusUpdate()
{
    QString scriptPath = ConfigManager::instance().getScriptPath("printer_comms.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();

    QProcess process;
    process.start("python3", QStringList() << "-c" << QString("import sys; sys.path.append('%1'); from printer_comms import get_status; print(get_status('%2'))").arg(QFileInfo(scriptPath).absolutePath(), printerIP));
    process.waitForFinished();

    QByteArray output = process.readAllStandardOutput();
    QByteArray error = process.readAllStandardError();

    if (error.isEmpty()) {
        QString result = QString::fromUtf8(output);

        // Parse status for short display
        if (result.contains("status:") && result.contains("current_layer:")) {
            QStringList lines = result.split('\n');
            QString status, layer, progress;

            for (const QString &line : lines) {
                if (line.contains("status:")) {
                    status = line.split(":").last().trimmed();
                }
                if (line.contains("current_layer:")) {
                    layer = line.split(":").last().trimmed();
                }
                if (line.contains("percent_complete:")) {
                    progress = line.split(":").last().trimmed();
                }
            }

            if (!status.isEmpty()) {
                QString shortStatus = QString("[AUTO] Status: %1 | Layer: %2 | Progress: %3%")
                    .arg(status.toUpper())
                    .arg(layer.isEmpty() ? "0" : layer)
                    .arg(progress.isEmpty() ? "0" : progress);
                ui->textBrowser->append(shortStatus);
                ui->statusLabel->setText(QString("Status: %1").arg(status.toUpper()));
            }
        }
    }
}

void Dialog::on_startPr_clicked()
{
    // Get paths from ConfigManager
    QString recipePath = ConfigManager::instance().getRecipePath();
    QString scriptPath = ConfigManager::instance().getScriptPath("print_manager.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();

    // Check if recipe file exists
    if (!QFileInfo::exists(recipePath))
    {
        QMessageBox::critical(this, "Recipe Error",
            QString("Recipe file not found: %1\n\nPlease create a recipe first using the 'Set' button above.").arg(recipePath));
        return;
    }

    // Check if print manager script exists
    if (!QFileInfo::exists(scriptPath))
    {
        QMessageBox::critical(this, "Script Error",
            QString("Print manager script not found: %1").arg(scriptPath));
        return;
    }

    if (!pythonProcess)
    {
        ui->textBrowser->append("=== STARTING MULTI-MATERIAL PRINT MANAGER ===");
        ui->textBrowser->append(QString("Recipe: %1").arg(recipePath));
        ui->textBrowser->append(QString("Script: %1").arg(scriptPath));
        ui->textBrowser->append(QString("Printer IP: %1").arg(printerIP));

        pythonProcess = new QProcess(this);
        connect(pythonProcess, &QProcess::readyReadStandardOutput, this, [this]() {
            QString output = pythonProcess->readAllStandardOutput();
            ui->textBrowser->append(output);
        });

        connect(pythonProcess, &QProcess::readyReadStandardError, this, [this]() {
            QString error = pythonProcess->readAllStandardError();
            if (!error.isEmpty()) {
                ui->textBrowser->append("ERROR: " + error);
            }
        });

        connect(pythonProcess, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
                this, [this](int exitCode, QProcess::ExitStatus exitStatus) {
            ui->textBrowser->append("=== PRINT MANAGER FINISHED ===");
            ui->textBrowser->append(QString("Exit code: %1").arg(exitCode));
            if (exitCode != 0) {
                ui->textBrowser->append("Print manager exited with error");
            }
            // Stop auto status polling when print manager finishes
            statusTimer->stop();
        });
    }
    else
    {
        ui->textBrowser->append("Stopping existing print manager...");
        pythonProcess->terminate();
        pythonProcess->waitForFinished(3000);
        statusTimer->stop();
    }

    // Build command arguments for print_manager.py
    QStringList arguments;
    arguments << scriptPath;
    arguments << "--recipe" << recipePath;
    arguments << "--printer-ip" << printerIP;

    ui->textBrowser->append("Starting automated multi-material printing...");
    ui->textBrowser->append(QString("Command: python3 %1 --recipe %2 --printer-ip %3").arg(scriptPath, recipePath, printerIP));

    pythonProcess->start("python3", arguments);

    if (!pythonProcess->waitForStarted(5000)) {
        ui->textBrowser->append("ERROR: Failed to start print manager");
        ui->textBrowser->append(QString("Process error: %1").arg(pythonProcess->errorString()));
        QMessageBox::critical(this, "Process Error",
            QString("Failed to start print manager:\n%1").arg(pythonProcess->errorString()));
    } else {
        ui->textBrowser->append("✓ Print manager started successfully - monitoring printer for material changes");
        // Start auto status polling every 5 seconds
        statusTimer->start(5000);
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
       if (result.trimmed().isEmpty()) {
           result = "Stop command sent successfully (no response from printer)";
       }
       QMessageBox::information(this, "Stop Printer Result", QString("Stop printer command executed.\n\nResponse: %1").arg(result));
       ui->textBrowser->append("[STOP] Stop command sent:");
       ui->textBrowser->append(result);
    }
    else
    {
       QString errorMessage = QString::fromUtf8(error);
       QMessageBox::critical(this, "Stop Printer Error", QString("Failed to stop printer.\n\nError: %1").arg(errorMessage));
       ui->textBrowser->append("ERROR: " + errorMessage);
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
       ui->textBrowser->append("[STATUS] Printer Status:");
       ui->textBrowser->append(result);
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
       ui->textBrowser->append("[PAUSE] Print paused successfully:");
       ui->textBrowser->append(result);
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
       ui->textBrowser->append("[RESUME] Print resumed successfully:");
       ui->textBrowser->append(result);
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

    // Enhanced logging for input validation
    ui->textBrowser->append("[PUMP] Starting pump operation:");
    ui->textBrowser->append(QString("Input: %1").arg(inputText));

    // Split the input using a comma as the delimiter
    QStringList inputValues = inputText.split(",");

    if (inputValues.size() != 3)
    {
        ui->textBrowser->append("[ERROR] Invalid pump format - expected: Motor,Direction,Timing");
        QMessageBox::critical(this, "Motor Control Error",
            QString("Invalid input format.\n\n"
                   "Expected: Motor,Direction,Timing (e.g., 'A,F,5')\n"
                   "You provided: %1 values\n"
                   "Raw input: '%2'").arg(inputValues.size()).arg(inputText));
        return;
    }
    QString argumentMotor = inputValues[0].trimmed();
    QString argumentDirection = inputValues[1].trimmed();
    QString argumentTiming = inputValues[2].trimmed();

    // Validate motor parameter
    if (!argumentMotor.isEmpty() && !(argumentMotor == "A" || argumentMotor == "B" || argumentMotor == "C" || argumentMotor == "D")) {
        ui->textBrowser->append(QString("[ERROR] Invalid motor '%1' - must be A, B, C, or D").arg(argumentMotor));
        QMessageBox::critical(this, "Motor Control Error",
            QString("Invalid motor '%1'.\nMust be A, B, C, or D").arg(argumentMotor));
        return;
    }

    // Validate direction parameter
    if (!argumentDirection.isEmpty() && !(argumentDirection == "F" || argumentDirection == "R")) {
        ui->textBrowser->append(QString("[ERROR] Invalid direction '%1' - must be F or R").arg(argumentDirection));
        QMessageBox::critical(this, "Motor Control Error",
            QString("Invalid direction '%1'.\nMust be F (forward) or R (reverse)").arg(argumentDirection));
        return;
    }

    // Validate and convert timing parameter
    bool timingOk;
    int intargumentTiming = argumentTiming.toInt(&timingOk);
    if (!timingOk || intargumentTiming <= 0) {
        ui->textBrowser->append(QString("[ERROR] Invalid timing '%1' - must be positive integer").arg(argumentTiming));
        QMessageBox::critical(this, "Motor Control Error",
            QString("Invalid timing '%1'.\nMust be a positive integer representing duration in seconds").arg(argumentTiming));
        return;
    }

    ui->textBrowser->append(QString("[PUMP] Running Motor %1 %2 for %3 seconds").arg(argumentMotor).arg(argumentDirection == "F" ? "forward" : "reverse").arg(intargumentTiming));

    // Build and log the Python command
    QString terminalCommand = QString("python3 -c \"import sys; sys.path.append('%1'); from %2 import %3; %3('%4', '%5', %6)\"")
        .arg(QFileInfo(scriptPath).absolutePath())
        .arg(QFileInfo(scriptPath).baseName())
        .arg(functionName)
        .arg(argumentMotor)
        .arg(argumentDirection)
        .arg(intargumentTiming);

    if (!pythonFunction)
    {
        pythonFunction = new QProcess(this);

        // Enhanced output handling with pump-specific logging
        connect(pythonFunction, &QProcess::readyReadStandardOutput, this, [this]() {
            QString output = QString::fromUtf8(pythonFunction->readAllStandardOutput());
            if (!output.isEmpty()) {
                ui->textBrowser->append(QString("[PUMP OUTPUT] %1").arg(output.trimmed()));
            }
        });

        // Add error output handling
        connect(pythonFunction, &QProcess::readyReadStandardError, this, [this]() {
            QString error = QString::fromUtf8(pythonFunction->readAllStandardError());
            if (!error.isEmpty()) {
                ui->textBrowser->append(QString("[PUMP ERROR] %1").arg(error.trimmed()));
            }
        });

        // Add process state change handling
        connect(pythonFunction, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
                this, [this](int exitCode, QProcess::ExitStatus exitStatus) {
            if (exitCode == 0) {
                ui->textBrowser->append("[PUMP] Operation completed successfully");
            } else {
                ui->textBrowser->append(QString("[PUMP] Operation failed with exit code %1").arg(exitCode));
            }
        });
    }
    else
    {
        ui->textBrowser->append("[PUMP] Stopping previous pump operation...");
        pythonFunction->terminate();
        pythonFunction->waitForFinished(3000); // Wait up to 3 seconds
    }

    pythonFunction->start("/bin/bash", QStringList() << "-c" << terminalCommand);

    if (!pythonFunction->waitForStarted(5000)) {
        ui->textBrowser->append("[ERROR] Failed to start pump control process");
    } else {
        ui->textBrowser->append("[PUMP] Process started successfully");
    }
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
       ui->textBrowser->append("[FILES] Available print files:");
       ui->textBrowser->append(result);
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
       ui->textBrowser->append("[PRINT START] Starting print file:");
       ui->textBrowser->append(result);
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
        ui->textBrowser->append("[PUMP] Stopped motor operation");
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
        ui->textBrowser->append("[PRINT] Stopped multi-material print manager");
        pythonProcess->terminate();
        pythonProcess->waitForFinished();
        pythonProcess->deleteLater();
        pythonProcess = nullptr;
        statusTimer->stop();
    }
}
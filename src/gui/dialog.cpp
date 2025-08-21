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
#include <QNetworkInterface>
#include <QNetworkAddressEntry>
#include <QFileDialog>
#include <QProcessEnvironment>
#include <QInputDialog>
#include <QStringList>
#include <QTableWidget>
#include <QComboBox>
#include <QSpinBox>
#include <QHeaderView>
#include <QThread>
#include <QSet>
#include <QApplication>
#include <QScreen>
#include <QShortcut>
#include <QMessageBox>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include "scriptworker.h"

Dialog::Dialog(QWidget *parent)
    : QDialog(parent), ui(new Ui::Dialog), pythonProcess(nullptr), autoUpdateEnabled(false)
{

    ui->setupUi(this);
    
    // Optimize for small screens
    optimizeForSmallScreen();
    
    setupRecipeTable();
    setupTooltips();
    setupKeyboardShortcuts();
    setupClearOutputButton();
    
    // Initialize status update timer
    statusUpdateTimer = new QTimer(this);
    connect(statusUpdateTimer, &QTimer::timeout, this, &Dialog::updateStatusDisplay);
    
    // Set up worker thread for asynchronous operations
    workerThread = new QThread(this);
    scriptWorker = new ScriptWorker();
    scriptWorker->moveToThread(workerThread);
    
    // Connect worker signals to dialog slots
    connect(scriptWorker, &ScriptWorker::scriptOutput, this, &Dialog::handleScriptOutput);
    connect(scriptWorker, &ScriptWorker::scriptError, this, &Dialog::handleScriptError);
    connect(scriptWorker, &ScriptWorker::scriptFinished, this, &Dialog::handleScriptFinished);
    connect(scriptWorker, &ScriptWorker::statusResult, this, &Dialog::handleStatusResult);
    connect(scriptWorker, &ScriptWorker::operationStarted, this, &Dialog::handleOperationStarted);
    connect(scriptWorker, &ScriptWorker::connectionLost, this, &Dialog::handleConnectionLost);
    connect(scriptWorker, &ScriptWorker::hardwareError, this, &Dialog::handleHardwareError);
    
    // Connect button state management to operation events
    connect(scriptWorker, &ScriptWorker::operationStarted, this, [this]() { setButtonStates(false); });
    connect(scriptWorker, &ScriptWorker::scriptFinished, this, [this]() { setButtonStates(true); });
    
    // Start the worker thread
    workerThread->start();
    
    // Connect button signal to slot
}

Dialog::~Dialog()
{
    // Clean up table widgets first
    clearRecipeTableWidgets();
    
    // Clean up any active processes
    if (pythonProcess && pythonProcess->state() != QProcess::NotRunning)
    {
        pythonProcess->terminate();
        pythonProcess->waitForFinished(3000);
        pythonProcess->deleteLater();
        pythonProcess = nullptr;
    }
    
    if (pythonFunction && pythonFunction->state() != QProcess::NotRunning)
    {
        pythonFunction->terminate();
        pythonFunction->waitForFinished(3000);
        pythonFunction->deleteLater();
        pythonFunction = nullptr;
    }
    
    // Clean up worker thread properly
    if (scriptWorker)
    {
        QMetaObject::invokeMethod(scriptWorker, "stopCurrentProcess", Qt::BlockingQueuedConnection);
        scriptWorker->deleteLater(); // Use deleteLater for thread-safe cleanup
        scriptWorker = nullptr;
    }
    
    if (workerThread && workerThread->isRunning())
    {
        workerThread->quit();
        if (!workerThread->wait(3000))
        {
            workerThread->terminate();
            workerThread->wait(1000);
        }
    }
    
    // Stop timers
    if (statusUpdateTimer)
    {
        statusUpdateTimer->stop();
    }
    
    if (timer)
    {
        timer->stop();
    }
    
    delete ui;
}

void Dialog::on_submitline_clicked()
{
    QString recipeText = generateRecipeString();  // Generate recipe from table
    QString filename = ConfigManager::instance().getRecipePath();  // Use config manager for recipe path

    QFile file(filename);
    if (file.open(QIODevice::WriteOnly | QIODevice::Text))
    {
        QTextStream stream(&file);
        stream << recipeText;  // Write the recipe text to the file
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

    // Only create the timer once
    if (!timer)
    {
        timer = new QTimer(this);
        connect(timer, &QTimer::timeout, this, [this]() { 
            updateConnectionStatus(); 
        });
        timer->start(5000);  // Adjust the interval (in milliseconds) according to your needs
    }
}

void Dialog::updateConnectionStatus()
{
    // This method is called by the timer to periodically check status
    updateStatusDisplay();
}

void Dialog::on_startPr_clicked()
{
    QString pythonScriptPath = getFileSelection();

    if (!pythonScriptPath.isEmpty())
    {
        // Clean up any existing process
        if (pythonProcess && pythonProcess->state() != QProcess::NotRunning)
        {
            pythonProcess->terminate();
            pythonProcess->waitForFinished(3000);
            pythonProcess->deleteLater();
            pythonProcess = nullptr;
        }
        
        if (!pythonProcess)
        {
            ui->textBrowser->append("Started Print...");
            pythonProcess = new QProcess(this);
            
            // Connect signals for proper process monitoring
            connect(pythonProcess, &QProcess::readyReadStandardOutput, this, [this]() {
                QString output = pythonProcess->readAllStandardOutput();
                ui->textBrowser->append(output);
            });
            
            connect(pythonProcess, &QProcess::readyReadStandardError, this, [this]() {
                QString error = pythonProcess->readAllStandardError();
                ui->textBrowser->append("ERROR: " + error);
            });
            
            connect(pythonProcess, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
                this, [this](int exitCode, QProcess::ExitStatus /*exitStatus*/) {
                    ui->textBrowser->append(QString("Process finished with exit code: %1").arg(exitCode));
                    pythonProcess->deleteLater();
                    pythonProcess = nullptr;
                });
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
    QString scriptPath = ConfigManager::instance().getScriptPath("newmonox.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString command = "gostop,end";
    
    ui->textBrowser->append("Stopping printer...");
    
    QMetaObject::invokeMethod(scriptWorker, "executeCommand", Qt::QueuedConnection,
                              Q_ARG(QString, scriptPath),
                              Q_ARG(QString, printerIP),
                              Q_ARG(QString, command));
}

void Dialog::on_checkstatus_clicked()
{
    updateStatusDisplay();
}

void Dialog::on_pausePr_clicked()
{
    QString scriptPath = ConfigManager::instance().getScriptPath("newmonox.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString command = "gopause";
    
    ui->textBrowser->append("Pausing printer...");
    
    QMetaObject::invokeMethod(scriptWorker, "executeCommand", Qt::QueuedConnection,
                              Q_ARG(QString, scriptPath),
                              Q_ARG(QString, printerIP),
                              Q_ARG(QString, command));
}

void Dialog::on_resumePr_clicked()
{
    QString scriptPath = ConfigManager::instance().getScriptPath("newmonox.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString command = "goresume";
    
    ui->textBrowser->append("Resuming printer...");
    
    QMetaObject::invokeMethod(scriptWorker, "executeCommand", Qt::QueuedConnection,
                              Q_ARG(QString, scriptPath),
                              Q_ARG(QString, printerIP),
                              Q_ARG(QString, command));
}

void Dialog::on_manualrun_clicked()
{
    QString scriptPath = ConfigManager::instance().getScriptPath("photonmmu_pump.py");
    QString functionName = "run_stepper";

    // Set the input text from the line edit
    QString inputText = ui->motor_settings->text().trimmed();
    
    // Validate input format before processing
    if (!validateMotorControlInput(inputText)) {
        return; // Error message already shown in validation function
    }
    
    ui->textBrowser->append("Motor command: " + inputText);

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

    // Clean up any existing pythonFunction process
    if (pythonFunction && pythonFunction->state() != QProcess::NotRunning)
    {
        pythonFunction->terminate();
        pythonFunction->waitForFinished(3000);
        pythonFunction->deleteLater();
        pythonFunction = nullptr;
    }
    
    if (!pythonFunction)
    {
        ui->textBrowser->append("Started Motor...");
        pythonFunction = new QProcess(this);
        
        connect(pythonFunction, &QProcess::readyReadStandardOutput, this, [this]() {
            QString output = QString::fromUtf8(pythonFunction->readAllStandardOutput());
            ui->textBrowser->append("\n******MOTOR RUNNING******\n");
            ui->textBrowser->append(output);
            ui->textBrowser->append("\n******END MOTOR RUNNING******");
        });
        
        connect(pythonFunction, &QProcess::readyReadStandardError, this, [this]() {
            QString error = QString::fromUtf8(pythonFunction->readAllStandardError());
            ui->textBrowser->append("Motor ERROR: " + error);
        });
        
        connect(pythonFunction, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, [this](int exitCode, QProcess::ExitStatus /*exitStatus*/) {
                ui->textBrowser->append(QString("Motor process finished with exit code: %1").arg(exitCode));
                pythonFunction->deleteLater();
                pythonFunction = nullptr;
            });
    }

    pythonFunction->start("/bin/bash", QStringList() << "-c" << terminalCommand);



    //QProcess process(this);



    //QString output = process.readAllStandardOutput();
    //QString error = process.readAllStandardError();

    //ui->textBrowser->setText(output);
   // QMessageBox::information(this, "Output", output);
}


void Dialog::on_getFiles_clicked()
{
    QString scriptPath = ConfigManager::instance().getScriptPath("newmonox.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString pythonCommand = QString("python3 %1 -i %2 -c getfiles").arg(scriptPath, printerIP);
    ui->textBrowser->append(pythonCommand);
    ui->filesWidget->clear();
    
    QProcess process;
    process.start("python3", QStringList() << scriptPath << "-i" << printerIP << "-c" << "getfiles");
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
    QString scriptPath = ConfigManager::instance().getScriptPath("newmonox.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    QString internalname = "";
    QString externalname = "";
    QString pythonCommand = QString("python3 %1 -i %2 -c goprint,").arg(scriptPath, printerIP);
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
            pythonCommand.append(internalname);
            pythonCommand+=",end";
            ui->textBrowser->append(pythonCommand);
        }
    }
    else
    {
        return; // User cancelled
    }


    QProcess process;
    process.start("python3", QStringList() << scriptPath << "-i" << printerIP << "-c" << QString("goprint,%1,end").arg(internalname));
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
        ui->textBrowser->append("Stopping Motor...");
        pythonFunction->terminate();
        if (!pythonFunction->waitForFinished(3000))
        {
            pythonFunction->kill();
            pythonFunction->waitForFinished(1000);
        }
        pythonFunction->deleteLater();
        pythonFunction = nullptr;
        ui->textBrowser->append("Motor stopped.");
    }
    else
    {
        ui->textBrowser->append("No motor process running.");
    }
}

void Dialog::on_stopMM_clicked()
{
    if (pythonProcess && pythonProcess->state() != QProcess::NotRunning)
    {
        ui->textBrowser->append("Stopping Multi-Material process...");
        pythonProcess->terminate();
        if (!pythonProcess->waitForFinished(3000))
        {
            pythonProcess->kill();
            pythonProcess->waitForFinished(1000);
        }
        pythonProcess->deleteLater();
        pythonProcess = nullptr;
        ui->textBrowser->append("Multi-Material process stopped.");
    }
    else
    {
        ui->textBrowser->append("No Multi-Material process running.");
    }
}

void Dialog::setupRecipeTable()
{
    // Set up the recipe table with proper formatting
    ui->recipeTable->setColumnCount(2);
    QStringList headers;
    headers << "Layer Number" << "Material Pump";
    ui->recipeTable->setHorizontalHeaderLabels(headers);
    
    // Set column widths
    ui->recipeTable->setColumnWidth(0, 120);
    ui->recipeTable->setColumnWidth(1, 150);
    
    // Enable row selection and alternating colors
    ui->recipeTable->setSelectionBehavior(QAbstractItemView::SelectRows);
    ui->recipeTable->setAlternatingRowColors(true);
    
    // Stretch the last column
    ui->recipeTable->horizontalHeader()->setStretchLastSection(true);
    
    // Add an initial row
    addRecipeTableRow(1, "A");
}

void Dialog::addRecipeTableRow(int layerNum, const QString &material)
{
    int row = ui->recipeTable->rowCount();
    ui->recipeTable->insertRow(row);
    
    // Add spin box for layer number
    QSpinBox *layerSpinBox = new QSpinBox();
    layerSpinBox->setMinimum(1);
    layerSpinBox->setMaximum(9999);
    layerSpinBox->setValue(layerNum);
    ui->recipeTable->setCellWidget(row, 0, layerSpinBox);
    
    // Add combo box for material selection
    QComboBox *materialCombo = new QComboBox();
    materialCombo->addItems({"A", "B", "C", "D"});
    materialCombo->setCurrentText(material);
    ui->recipeTable->setCellWidget(row, 1, materialCombo);
}

QString Dialog::generateRecipeString()
{
    QStringList recipeEntries;
    
    for (int row = 0; row < ui->recipeTable->rowCount(); ++row)
    {
        QSpinBox *layerSpinBox = qobject_cast<QSpinBox*>(ui->recipeTable->cellWidget(row, 0));
        QComboBox *materialCombo = qobject_cast<QComboBox*>(ui->recipeTable->cellWidget(row, 1));
        
        if (layerSpinBox && materialCombo)
        {
            QString entry = QString("%1,%2").arg(materialCombo->currentText()).arg(layerSpinBox->value());
            recipeEntries.append(entry);
        }
    }
    
    return recipeEntries.join(":");
}

void Dialog::on_addRecipeRow_clicked()
{
    // Determine the next layer number
    int nextLayer = 1;
    if (ui->recipeTable->rowCount() > 0)
    {
        QSpinBox *lastLayerSpinBox = qobject_cast<QSpinBox*>(ui->recipeTable->cellWidget(ui->recipeTable->rowCount() - 1, 0));
        if (lastLayerSpinBox)
        {
            nextLayer = lastLayerSpinBox->value() + 1;
        }
    }
    
    addRecipeTableRow(nextLayer, "A");
}

void Dialog::on_removeRecipeRow_clicked()
{
    int currentRow = ui->recipeTable->currentRow();
    if (currentRow >= 0)
    {
        ui->recipeTable->removeRow(currentRow);
    }
    else
    {
        QMessageBox::information(this, "No Selection", "Please select a row to remove.");
    }
}

void Dialog::on_loadRecipe_clicked()
{
    QString filename = QFileDialog::getOpenFileName(this, "Load Recipe File", 
                                                   ConfigManager::instance().getConfigPath(),
                                                   "Recipe Files (*.txt);;All Files (*)");
    
    if (!filename.isEmpty())
    {
        QFile file(filename);
        if (file.open(QIODevice::ReadOnly | QIODevice::Text))
        {
            QTextStream stream(&file);
            QString recipeText = stream.readAll();
            file.close();
            
            // Clear the current table properly
            clearRecipeTableWidgets();
            
            // Parse the recipe text and populate the table
            QStringList entries = recipeText.split(":");
            for (const QString &entry : entries)
            {
                QStringList parts = entry.split(",");
                if (parts.size() == 2)
                {
                    QString material = parts[0].trimmed();
                    int layerNum = parts[1].trimmed().toInt();
                    addRecipeTableRow(layerNum, material);
                }
            }
            
            QMessageBox::information(this, "Recipe Loaded", "Recipe has been loaded successfully.");
        }
        else
        {
            QMessageBox::critical(this, "Error", "Failed to load the recipe file.");
        }
    }
}

void Dialog::on_toggleAutoUpdate_clicked()
{
    autoUpdateEnabled = !autoUpdateEnabled;
    
    if (autoUpdateEnabled)
    {
        ui->toggleAutoUpdate->setText("Auto Update: ON");
        statusUpdateTimer->start(5000); // Update every 5 seconds
    }
    else
    {
        ui->toggleAutoUpdate->setText("Auto Update: OFF");
        statusUpdateTimer->stop();
    }
}

void Dialog::updateStatusDisplay()
{
    QString scriptPath = ConfigManager::instance().getScriptPath("newmonox.py");
    QString printerIP = ConfigManager::instance().getPrinterIP();
    
    // Use async worker instead of blocking operation
    QMetaObject::invokeMethod(scriptWorker, "checkStatus", Qt::QueuedConnection,
                              Q_ARG(QString, scriptPath),
                              Q_ARG(QString, printerIP));
}

void Dialog::parseStatusResponse(const QString &response)
{
    // Parse the printer status response and update UI elements
    // This is a basic parser - might need adjustment based on actual response format
    
    if (response.contains("printing", Qt::CaseInsensitive))
    {
        ui->printerStateValue->setText("Printing");
        ui->printerStateValue->setStyleSheet("color: green;");
    }
    else if (response.contains("paused", Qt::CaseInsensitive))
    {
        ui->printerStateValue->setText("Paused");
        ui->printerStateValue->setStyleSheet("color: orange;");
    }
    else if (response.contains("idle", Qt::CaseInsensitive))
    {
        ui->printerStateValue->setText("Idle");
        ui->printerStateValue->setStyleSheet("color: blue;");
    }
    else
    {
        ui->printerStateValue->setText("Unknown");
        ui->printerStateValue->setStyleSheet("color: gray;");
    }
    
    // Extract current file information if available
    QRegExp fileRegex("file[:\\s]+([^\\n\\r]+)", Qt::CaseInsensitive);
    if (fileRegex.indexIn(response, 0) != -1)
    {
        ui->currentFileValue->setText(fileRegex.cap(1).trimmed());
    }
    
    // Extract progress if available (looking for percentage patterns)
    QRegExp progressRegex("(\\d+)%");
    if (progressRegex.indexIn(response) != -1)
    {
        int progress = progressRegex.cap(1).toInt();
        ui->printProgressBar->setValue(progress);
    }
    
    // Update next material change info
    ui->nextMaterialValue->setText(getNextMaterialChange());
}

void Dialog::updateConnectionStatus(bool connected)
{
    if (connected)
    {
        ui->connectionStatusValue->setText("Connected");
        ui->connectionStatusValue->setStyleSheet("color: green;");
    }
    else
    {
        ui->connectionStatusValue->setText("Disconnected");
        ui->connectionStatusValue->setStyleSheet("color: red;");
        
        // Reset other status fields when disconnected
        ui->printerStateValue->setText("Unknown");
        ui->printerStateValue->setStyleSheet("color: gray;");
        ui->currentFileValue->setText("None");
        ui->printProgressBar->setValue(0);
        ui->nextMaterialValue->setText("N/A");
    }
}

QString Dialog::getNextMaterialChange()
{
    // Analyze the current recipe to determine the next material change
    if (ui->recipeTable->rowCount() == 0)
    {
        return "No recipe loaded";
    }
    
    // This is a simplified version - in a real implementation you'd track
    // current layer progress and compare with recipe
    QSpinBox *firstLayerSpinBox = qobject_cast<QSpinBox*>(ui->recipeTable->cellWidget(0, 0));
    QComboBox *firstMaterialCombo = qobject_cast<QComboBox*>(ui->recipeTable->cellWidget(0, 1));
    
    if (firstLayerSpinBox && firstMaterialCombo)
    {
        return QString("Layer %1: %2").arg(firstLayerSpinBox->value()).arg(firstMaterialCombo->currentText());
    }
    
    return "Recipe data unavailable";
}

void Dialog::on_startMultiMaterialPrint_clicked()
{
    ui->textBrowser->append("Starting Multi-Material Print Workflow...");
    
    // Step 1: Validate the complete setup
    if (!validatePrintSetup())
    {
        return; // Validation failed, messages already shown
    }
    
    // Step 2: Show confirmation dialog with print details
    QString recipeText = generateRecipeString();
    QString confirmationMessage = QString(
        "Ready to start multi-material print!\n\n"
        "Recipe: %1\n\n"
        "Material changes: %2\n\n"
        "Printer connection: %3\n\n"
        "Are you sure you want to start printing?"
    ).arg(recipeText)
     .arg(ui->recipeTable->rowCount())
     .arg(ui->connectionStatusValue->text());
    
    QMessageBox::StandardButton reply = QMessageBox::question(
        this, 
        "Confirm Multi-Material Print", 
        confirmationMessage,
        QMessageBox::Yes | QMessageBox::No
    );
    
    if (reply != QMessageBox::Yes)
    {
        ui->textBrowser->append("Print cancelled by user.");
        return;
    }
    
    // Step 3: Final pre-print checks
    ui->textBrowser->append("Performing final pre-print validation...");
    updateStatusDisplay(); // Check current printer status
    
    // Step 4: Save the current recipe automatically
    on_submitline_clicked();
    
    // Step 5: Start the multi-material print process
    QString pythonScriptPath = getFileSelection();
    
    if (!pythonScriptPath.isEmpty())
    {
        ui->textBrowser->append("Starting multi-material print with selected file...");
        
        if (!pythonProcess)
        {
            ui->textBrowser->append("Initiating Multi-Material Print Process...");
            pythonProcess = new QProcess(this);
            connect(pythonProcess, &QProcess::readyReadStandardOutput, this, [this]() {
                QString output = pythonProcess->readAllStandardOutput();
                ui->textBrowser->append(output);
            });
            
            connect(pythonProcess, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
                this, [this](int /*exitCode*/, QProcess::ExitStatus exitStatus) {
                    if (exitStatus == QProcess::NormalExit)
                    {
                        ui->textBrowser->append("Multi-material print process completed.");
                    }
                    else
                    {
                        ui->textBrowser->append("Multi-material print process terminated unexpectedly.");
                    }
                });
        }
        else
        {
            pythonProcess->terminate();
            pythonProcess->waitForFinished();
        }
        
        pythonProcess->start("python3", QStringList() << pythonScriptPath);
        
        // Enable auto-status updates during printing
        if (!autoUpdateEnabled)
        {
            on_toggleAutoUpdate_clicked();
        }
    }
    else
    {
        QMessageBox::warning(this, "No File Selected", "Please select a print file to continue.");
    }
}

bool Dialog::validatePrintSetup()
{
    QStringList validationErrors;
    QStringList warnings;
    
    // Check recipe
    if (!validateRecipe())
    {
        validationErrors << "Invalid or empty recipe";
    }
    
    // Check connection
    if (!validateConnection())
    {
        validationErrors << "Printer not connected";
    }
    
    // Check for other potential issues
    if (ui->printerStateValue->text() == "Printing")
    {
        validationErrors << "Printer is already printing";
    }
    
    // Check for warning conditions
    if (ui->printerStateValue->text() == "Unknown")
    {
        warnings << "Printer state is unknown - status may be outdated";
    }
    
    // Check if recipe has valid layer sequencing
    if (ui->recipeTable->rowCount() > 1)
    {
        QSet<int> usedLayers;
        for (int row = 0; row < ui->recipeTable->rowCount(); ++row)
        {
            QSpinBox *layerSpinBox = qobject_cast<QSpinBox*>(ui->recipeTable->cellWidget(row, 0));
            if (layerSpinBox)
            {
                int layer = layerSpinBox->value();
                if (usedLayers.contains(layer))
                {
                    warnings << QString("Duplicate layer number: %1").arg(layer);
                }
                usedLayers.insert(layer);
            }
        }
    }
    
    // Show warnings if any
    if (!warnings.isEmpty())
    {
        QString warningMessage = "Warning: The following issues were detected:\n\n• " 
                              + warnings.join("\n• ") + "\n\nDo you want to continue anyway?";
        QMessageBox::StandardButton reply = QMessageBox::question(this, "Validation Warnings", 
                                                                 warningMessage,
                                                                 QMessageBox::Yes | QMessageBox::No);
        if (reply != QMessageBox::Yes)
        {
            ui->textBrowser->append("Print cancelled due to validation warnings.");
            return false;
        }
    }
    
    // Critical errors prevent printing
    if (!validationErrors.isEmpty())
    {
        QString errorMessage = "Cannot start print. Please fix the following issues:\n\n• " 
                              + validationErrors.join("\n• ");
        QMessageBox::critical(this, "Pre-Print Validation Failed", errorMessage);
        ui->textBrowser->append("Pre-print validation failed: " + validationErrors.join(", "));
        return false;
    }
    
    ui->textBrowser->append("Pre-print validation passed successfully.");
    return true;
}

bool Dialog::validateRecipe()
{
    if (ui->recipeTable->rowCount() == 0)
    {
        return false;
    }
    
    // Check that each row has valid data
    for (int row = 0; row < ui->recipeTable->rowCount(); ++row)
    {
        QSpinBox *layerSpinBox = qobject_cast<QSpinBox*>(ui->recipeTable->cellWidget(row, 0));
        QComboBox *materialCombo = qobject_cast<QComboBox*>(ui->recipeTable->cellWidget(row, 1));
        
        if (!layerSpinBox || !materialCombo)
        {
            return false;
        }
        
        if (layerSpinBox->value() < 1)
        {
            return false;
        }
    }
    
    return true;
}

bool Dialog::validateConnection()
{
    return ui->connectionStatusValue->text() == "Connected";
}

void Dialog::handleScriptOutput(const QString &output)
{
    ui->textBrowser->append(output);
}

void Dialog::handleScriptError(const QString &error)
{
    ui->textBrowser->append("ERROR: " + error);
}

void Dialog::handleScriptFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    if (exitStatus == QProcess::NormalExit)
    {
        if (exitCode == 0)
        {
            ui->textBrowser->append("Operation completed successfully.");
        }
        else
        {
            ui->textBrowser->append(QString("Operation completed with exit code: %1").arg(exitCode));
        }
    }
    else
    {
        ui->textBrowser->append("Operation was terminated unexpectedly.");
    }
}

void Dialog::handleStatusResult(const QString &statusText, bool success)
{
    if (success)
    {
        parseStatusResponse(statusText);
        updateConnectionStatus(true);
        
        if (!autoUpdateEnabled) // Only show detailed output when manually checking
        {
            ui->textBrowser->append("\n******STATUS******\n");
            ui->textBrowser->append(statusText);
            ui->textBrowser->append("******END STATUS******");
        }
    }
    else
    {
        updateConnectionStatus(false);
        if (!autoUpdateEnabled) // Only show error when manually checking
        {
            ui->textBrowser->append("Status check failed: " + statusText);
        }
    }
}

void Dialog::handleOperationStarted()
{
    // Could add a progress indicator or status message here
    // For now, we'll just indicate that an operation is in progress
}

void Dialog::handleConnectionLost()
{
    // Update UI to reflect lost connection
    updateConnectionStatus(false);
    
    // Show user notification
    QMessageBox::critical(this, "Connection Lost", 
                         "Connection to the printer has been lost. Please check:\n\n"
                         "• Network connection\n"
                         "• Printer power status\n"
                         "• IP address configuration\n\n"
                         "Auto-updates will be disabled until connection is restored.");
    
    ui->textBrowser->append("*** CONNECTION LOST ***");
    
    // Disable auto-updates if they were enabled
    if (autoUpdateEnabled)
    {
        on_toggleAutoUpdate_clicked();
    }
    
    // Log the connection loss
    ui->textBrowser->append("Connection monitoring: Multiple consecutive failures detected");
}

void Dialog::handleHardwareError(const QString &errorDescription)
{
    // Show critical hardware error
    QMessageBox::critical(this, "Hardware Error", 
                         QString("Hardware error detected:\n\n%1\n\n"
                                 "Please check the system and resolve the issue before continuing.")
                         .arg(errorDescription));
    
    ui->textBrowser->append(QString("*** HARDWARE ERROR: %1 ***").arg(errorDescription));
    
    // Disable auto-updates to prevent continuous error messages
    if (autoUpdateEnabled)
    {
        on_toggleAutoUpdate_clicked();
    }
    
    // Consider stopping any active operations
    if (pythonProcess && pythonProcess->state() != QProcess::NotRunning)
    {
        QMessageBox::StandardButton reply = QMessageBox::question(this, 
            "Stop Current Operation", 
            "A hardware error has been detected. Do you want to stop the current operation?",
            QMessageBox::Yes | QMessageBox::No);
        
        if (reply == QMessageBox::Yes)
        {
            on_stopMM_clicked();
        }
    }
}

void Dialog::clearRecipeTableWidgets()
{
    // Properly clean up all custom widgets in the recipe table
    for (int row = 0; row < ui->recipeTable->rowCount(); ++row)
    {
        // Get the widgets and delete them explicitly
        QWidget* layerWidget = ui->recipeTable->cellWidget(row, 0);
        QWidget* materialWidget = ui->recipeTable->cellWidget(row, 1);
        
        if (layerWidget)
        {
            ui->recipeTable->removeCellWidget(row, 0);
            layerWidget->deleteLater();
        }
        
        if (materialWidget)
        {
            ui->recipeTable->removeCellWidget(row, 1);
            materialWidget->deleteLater();
        }
    }
    
    // Clear all rows
    ui->recipeTable->setRowCount(0);
}

void Dialog::optimizeForSmallScreen()
{
    // Get screen size using modern Qt API (fixes deprecation warning)
    QScreen *screen = QApplication::primaryScreen();
    if (!screen) return;
    
    QRect screenGeometry = screen->geometry();
    int screenWidth = screenGeometry.width();
    int screenHeight = screenGeometry.height();
    
    // If screen is small (like 1024x600), apply aggressive optimizations
    if (screenWidth <= 1024 || screenHeight <= 600)
    {
        // Much more aggressive window sizing - account for VNC status bar (~40px) and window decorations (~80px)
        int availableHeight = screenHeight - 120;
        resize(qMin(1000, screenWidth - 20), qMin(450, availableHeight));
        
        // Make recipe table extremely compact
        if (ui->recipeTable)
        {
            ui->recipeTable->setMaximumHeight(70);
            ui->recipeTable->setMinimumHeight(50);
        }
        
        // Allow text browser to expand and fill the right side completely
        if (ui->textBrowser)
        {
            ui->textBrowser->setMaximumHeight(16777215); // Remove height restriction
            ui->textBrowser->setMinimumHeight(120);      // Ensure minimum usable height
            ui->textBrowser->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
        }
        
        // Reduce margins and spacing to minimum
        if (layout())
        {
            layout()->setContentsMargins(2, 1, 2, 1);
            layout()->setSpacing(1);
        }
        
        // Make files widget extremely compact
        if (ui->filesWidget)
        {
            ui->filesWidget->setMaximumHeight(40);
        }
        
        // Apply compact stylesheet with larger, more readable text and proper title spacing
        setStyleSheet(styleSheet() + 
            "QGroupBox { font-size: 9pt; padding-top: 15px; margin-top: 5px; margin-bottom: 2px; }"
            "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px 0 5px; top: -7px; left: 10px; }"
            "QLabel { font-size: 9pt; min-width: 85px; }"
            "QPushButton { font-size: 9pt; padding: 1px 3px; max-height: 22px; }"
            "QTableWidget { font-size: 8pt; }"
            "QTextBrowser { font-size: 9pt; }" // Much larger text for output
            "QListWidget { font-size: 8pt; }"
            "QVBoxLayout { spacing: 1px; }"
            "QHBoxLayout { spacing: 2px; }"
            "QProgressBar { max-height: 14px; font-size: 8pt; }"
            "QComboBox, QSpinBox { font-size: 8pt; max-height: 20px; }"
            "QLineEdit { font-size: 8pt; max-height: 20px; }"
        );
        
        // Make status labels wider to prevent text cutoff
        if (ui->connectionStatusLabel) ui->connectionStatusLabel->setMinimumWidth(90);
        if (ui->printerStateLabel) ui->printerStateLabel->setMinimumWidth(90);
        if (ui->currentFileLabel) ui->currentFileLabel->setMinimumWidth(90);
        if (ui->progressLabel) ui->progressLabel->setMinimumWidth(90);
        if (ui->nextMaterialLabel) ui->nextMaterialLabel->setMinimumWidth(90);
        
        // Find all group boxes and apply layout with proper title space
        QList<QGroupBox*> groupBoxes = findChildren<QGroupBox*>();
        for (QGroupBox* groupBox : groupBoxes) {
            if (groupBox->layout()) {
                groupBox->layout()->setContentsMargins(5, 12, 5, 3); // More top margin for title
                groupBox->layout()->setSpacing(2);
            }
        }
        
        // Set window to be fully resizable and expandable
        setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
        setMaximumHeight(16777215); // Remove height restriction for maximizing
        
        // Ensure the main layout expands to fill all available space
        if (layout()) {
            layout()->setSizeConstraint(QLayout::SetDefaultConstraint);
        }
    }
}

void Dialog::setupTooltips()
{
    // Recipe management tooltips
    ui->addRecipeRow->setToolTip("Add a new layer for material change");
    ui->removeRecipeRow->setToolTip("Remove selected row from recipe");
    ui->loadRecipe->setToolTip("Load a previously saved recipe from file");
    ui->saveRecipe->setToolTip("Save current recipe to file");
    
    // Printer control tooltips
    ui->checkstatus->setToolTip("Check printer connection and current status");
    ui->toggleAutoUpdate->setToolTip("Enable/disable automatic status updates every 5 seconds");
    ui->startPr->setToolTip("Start print job on the printer");
    ui->pausePr->setToolTip("Pause current print job");
    ui->resumePr->setToolTip("Resume paused print job");
    ui->stopPr->setToolTip("Stop current print job completely");
    
    // Motor control tooltips
    ui->motor_settings->setToolTip("Enter motor command: PUMP,DIRECTION,TIME\nExample: A,F,30 (Pump A, Forward, 30 seconds)");
    ui->manualrun->setToolTip("Execute the motor command entered above");
    ui->stopMr->setToolTip("Stop currently running motor");
    
    // Multi-material tooltips
    ui->startMultiMaterialPrint->setToolTip("Start automated multi-material print with current recipe");
    ui->stopMM->setToolTip("Stop multi-material automation (printer continues normally)");
    
    // File management tooltips
    ui->getFiles->setToolTip("Refresh list of available print files on the printer");
    
    // Recipe table tooltip
    ui->recipeTable->setToolTip("Define material changes: Set layer numbers and select materials (A, B, C, D) for each change");
}

void Dialog::setupKeyboardShortcuts()
{
    // Create keyboard shortcuts for common actions
    QShortcut *saveShortcut = new QShortcut(QKeySequence("Ctrl+S"), this);
    connect(saveShortcut, &QShortcut::activated, this, &Dialog::on_saveRecipe_clicked);
    
    QShortcut *checkStatusShortcut = new QShortcut(QKeySequence("F5"), this);
    connect(checkStatusShortcut, &QShortcut::activated, this, &Dialog::on_checkstatus_clicked);
    
    QShortcut *startPrintShortcut = new QShortcut(QKeySequence("Ctrl+Shift+P"), this);
    connect(startPrintShortcut, &QShortcut::activated, this, &Dialog::on_startMultiMaterialPrint_clicked);
    
    QShortcut *addRowShortcut = new QShortcut(QKeySequence("Ctrl+Plus"), this);
    connect(addRowShortcut, &QShortcut::activated, this, &Dialog::on_addRecipeRow_clicked);
    
    QShortcut *removeRowShortcut = new QShortcut(QKeySequence("Delete"), this);
    connect(removeRowShortcut, &QShortcut::activated, this, &Dialog::on_removeRecipeRow_clicked);
}

bool Dialog::validateMotorControlInput(const QString &input)
{
    if (input.isEmpty()) {
        QMessageBox::warning(this, "Invalid Input", "Please enter a motor command.\nFormat: PUMP,DIRECTION,TIME\nExample: A,F,30");
        return false;
    }
    
    QStringList parts = input.split(",");
    if (parts.size() != 3) {
        QMessageBox::warning(this, "Invalid Input", "Motor command must have 3 parts separated by commas.\nFormat: PUMP,DIRECTION,TIME\nExample: A,F,30");
        return false;
    }
    
    // Validate pump (A, B, C, or D)
    QString pump = parts[0].trimmed().toUpper();
    if (!QStringList({"A", "B", "C", "D"}).contains(pump)) {
        QMessageBox::warning(this, "Invalid Pump", "Pump must be A, B, C, or D.\nYou entered: " + parts[0]);
        return false;
    }
    
    // Validate direction (F or R)
    QString direction = parts[1].trimmed().toUpper();
    if (!QStringList({"F", "R"}).contains(direction)) {
        QMessageBox::warning(this, "Invalid Direction", "Direction must be F (Forward) or R (Reverse).\nYou entered: " + parts[1]);
        return false;
    }
    
    // Validate time (positive number)
    bool ok;
    int time = parts[2].trimmed().toInt(&ok);
    if (!ok || time <= 0) {
        QMessageBox::warning(this, "Invalid Time", "Time must be a positive number (seconds).\nYou entered: " + parts[2]);
        return false;
    }
    
    if (time > 300) { // Sanity check - max 5 minutes
        QMessageBox::warning(this, "Time Too Long", "Time cannot exceed 300 seconds (5 minutes).\nYou entered: " + QString::number(time));
        return false;
    }
    
    return true;
}

void Dialog::setupClearOutputButton()
{
    // Create a small clear button and add it near the output area
    QPushButton *clearButton = new QPushButton("Clear Output", this);
    clearButton->setMaximumWidth(80);
    clearButton->setToolTip("Clear all text from the output area (Ctrl+L)");
    clearButton->setStyleSheet("QPushButton { font-size: 7pt; padding: 1px 2px; }");
    
    // Connect the button to clear the text browser
    connect(clearButton, &QPushButton::clicked, [this]() {
        ui->textBrowser->clear();
        ui->textBrowser->append("Output cleared.");
    });
    
    // Add keyboard shortcut for clearing output
    QShortcut *clearShortcut = new QShortcut(QKeySequence("Ctrl+L"), this);
    connect(clearShortcut, &QShortcut::activated, [this]() {
        ui->textBrowser->clear();
        ui->textBrowser->append("Output cleared.");
    });
    
    // Try to find a suitable layout to add the button to
    // We'll add it to the right side layout near the output area
    QWidget *outputWidget = ui->textBrowser->parentWidget();
    if (outputWidget && outputWidget->layout()) {
        // Find the layout containing the text browser and add button
        QVBoxLayout *outputLayout = qobject_cast<QVBoxLayout*>(outputWidget->layout());
        if (outputLayout) {
            QHBoxLayout *buttonLayout = new QHBoxLayout();
            buttonLayout->addStretch();
            buttonLayout->addWidget(clearButton);
            outputLayout->addLayout(buttonLayout);
        }
    }
}

void Dialog::setButtonStates(bool enabled)
{
    // Disable/enable buttons during operations to prevent conflicts
    ui->manualrun->setEnabled(enabled);
    ui->startPr->setEnabled(enabled);
    ui->pausePr->setEnabled(enabled);
    ui->resumePr->setEnabled(enabled);
    ui->stopPr->setEnabled(enabled);
    ui->startMultiMaterialPrint->setEnabled(enabled);
    ui->getFiles->setEnabled(enabled);
    
    // Update button text/style to indicate busy state
    if (!enabled) {
        ui->checkstatus->setText("Checking...");
        ui->checkstatus->setEnabled(false);
    } else {
        ui->checkstatus->setText("Check Status");
        ui->checkstatus->setEnabled(true);
    }
}

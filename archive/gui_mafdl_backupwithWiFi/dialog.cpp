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

Dialog::Dialog(QWidget *parent)
    : QDialog(parent), ui(new Ui::Dialog), pythonProcess(nullptr)
{

    ui->setupUi(this);
    // Connect button signal to slot
    connect(ui->refreshAPs, &QPushButton::clicked, this, &Dialog::selectAP);
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
                QString output = QString::fromUtf8(pythonProcess->readAllStandardOutput());
                QMessageBox::information(this, "Python Script Output", output);
                ui->textBrowser->append(output);
                });
            }
            else
            {
                pythonProcess->terminate();
                pythonProcess->waitForFinished();
            }

            pythonProcess->start("python", QStringList() << pythonScriptPath);
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
    if (pythonProcess && pythonProcess->state() != QProcess::NotRunning)
    {
        ui->textBrowser->append("Stopped Print...");
        pythonProcess->terminate();
        pythonProcess->waitForFinished();
        pythonProcess->deleteLater();
        pythonProcess = nullptr;
    }
    if (pythonFunction && pythonFunction->state() != QProcess::NotRunning)
    {
        ui->textBrowser->append("Stopped Motor...");
        pythonFunction->terminate();
        pythonFunction->waitForFinished();
        pythonFunction->deleteLater();
        pythonFunction = nullptr;
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

void Dialog::on_pausePr_clicked()
{
    QString pythonCommand = "python3 /home/pidlp/pidlp/dev/anycubic-python-master/src/uart_wifi/scripts/monox.py  -i 192.168.4.2 -c gopause";  // Replace with your desired Python command
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

void Dialog::on_resumePr_clicked()
{
    QString pythonCommand = "python3 /home/pidlp/pidlp/dev/anycubic-python-master/src/uart_wifi/scripts/monox.py  -i 192.168.4.2 -c goresume";  // Replace with your desired Python command
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

void Dialog::on_manualrun_clicked()
{
    QString scriptPath = "/home/pidlp/pidlp/dev/scripts/photonmmu_pump.py";
    QString functionName = "run_stepper";

    // Set the input text from the line edit
    QString inputText = ui->motor_settings->text();
    ui->textBrowser->setText(inputText);

    // Split the input using a comma as the delimiter
    QStringList inputValues = inputText.split(",");

if (inputValues.size() != 2)
    {
        // Incorrect Input format and display an error
        QMessageBox::critical(this, "Error", "Invalid input format. Expected format: A, F in Motor Control line");
        return;
    }
    QString argumentMotor = inputValues[0].trimmed();
    QString argumentDirection = inputValues[1].trimmed();

    QString terminalCommand = QString("python3 -c \"import sys; sys.path.append('%1'); from %2 import %3; %3('%4', '%5')\"")
        .arg(QFileInfo(scriptPath).absolutePath())
        .arg(QFileInfo(scriptPath).baseName())
        .arg(functionName)
        .arg(argumentMotor)
        .arg(argumentDirection);
    QString A = argumentMotor;
    QString B = argumentDirection;
    ui->textBrowser->setText(A);
    ui->textBrowser->setText(B);

    //pythonFunction = new QProcess;

    if (!pythonFunction)
    {
        ui->textBrowser->append("Started Motor...");
        pythonFunction = new QProcess(this);
        connect(pythonFunction, &QProcess::readyReadStandardOutput, this, [this]()   {
                QString output = QString::fromUtf8(pythonFunction->readAllStandardOutput());
                QMessageBox::information(this, "Motor Output", output);
                ui->textBrowser->append(output);
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

void Dialog::loadAndDisplaySTL(const QString &stlFilePath)
{
//   view3D = new Qt3DExtras::Qt3DWindow();
//   QWidget *container = QWidget::createWindowContainer(view3D);

//   mesh = new Qt3DRender::QMesh();
//   mesh->setSource(QUrl::fromLocalFile(stlFilePath));

//   Qt3DExtras::QOrbitCameraController *cameraController = new Qt3DExtras::QOrbitCameraController();
//   cameraController->setCamera(view3D->camera());

//   view3D->defaultFrameGraph()->clear();
//   view3D->setRootEntity(mesh);
//   view3D->setActiveFrameGraph(view3D->defaultFrameGraph());
//   view3D->camera()->setProjectionType(Qt3DRender::QCameraLens::PerspectiveProjection);
//   view3D->camera()->setPosition(QVector3D(0, 0, 2.0f));
//   view3D->camera()->setViewCenter(QVector3D(0, 0, 0));
//   view3D->camera()->setNearPlane(0.1f);
//   view3D->camera()->setFarPlane(1000.0f);

//   QVBoxLayout *layout = new QVBoxLayout(ui->stlContainer);
//   layout->addWidget(container);
}


void Dialog::selectAP()
{
    // Clear the AP list widget
    ui->listWidget->clear();

    // Run the iwlist command to get the available APs
    QProcess process;
    process.start("iwlist wlan0 scan");  // Replace "wlan0" with the appropriate wireless interface name

    if (!process.waitForFinished())
    {
        // Error running the command
        return;
    }

    // Parse the output of the command to extract AP information
    QString output = process.readAllStandardOutput();
    QStringList lines = output.split(QRegExp("[\r\n]"), QString::SkipEmptyParts);
    QStringList aps;

    for (const QString& line : lines)
    {
        if (line.contains("ESSID:"))
        {
            QString apName = line.section('"', 1, 1);
            if (!aps.contains(apName))
                aps.append(apName);
        }
    }

    // Populate the AP list widget with the available APs
    ui->listWidget->addItems(aps);

    // Connect the item clicked signal to a slot for handling AP connection
    connect(ui->listWidget, &QListWidget::itemClicked, this, &Dialog::connectToAP);
}

void Dialog::connectToAP(QListWidgetItem* item)
{

//    QString apName = item->text();

//    bool ok;
//    QString password = QInputDialog::getText(this, "Enter Wi-Fi Password", "Password:", QLineEdit::Password, "", &ok);

//    // Stop the wpa_supplicant service
//        QProcess::execute("sudo systemctl stop wpa_supplicant");

//        // Generate a network configuration file
//        QString configFile = "/tmp/wpa_supplicant.conf";
//        QString configContent = QString("network={\n"
//                                        "    ssid=\"%1\"\n"
//                                        "    psk=\"%2\"\n"
//                                        "}").arg(apName, password);

//    // Connect to the selected AP using the appropriate method for your use case
//    // This may involve running another system command or using a library specific to your requirements

//    if (ok && !password.isEmpty())
//    {


//        QFile file(configFile);
//            if (file.open(QIODevice::WriteOnly | QIODevice::Text))
//            {
//                QTextStream stream(&file);
//                stream << configContent;
//                file.close();

//                // Start the wpa_supplicant service with the generated configuration
//                QString command = QString("sudo wpa_supplicant -B -i wlan0 -c %1").arg(configFile);
//                int result = QProcess::execute(command);

//                if (result == 0)
//                {
//                    // Connection succeeded
//                    ui->statusLabel->setText("Connected");
//                }
//                else
//                {
//                    // Connection failed
//                    ui->statusLabel->setText("Disconnected");
//                    QMessageBox::critical(this, "Connection Failed", "Failed to connect to the Wi-Fi network.");
//                }

//                // Remove the temporary network configuration file
//                QFile::remove(configFile);
//            }
//            else
//            {
//                QMessageBox::critical(this, "Error", "Failed to create the network configuration file.");
//            }

//            // Restart the wpa_supplicant service
//            QProcess::execute("sudo systemctl start wpa_supplicant");
//    }
}

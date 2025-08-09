/********************************************************************************
** Form generated from reading UI file 'dialog.ui'
**
** Created by: Qt User Interface Compiler version 5.15.2
**
** WARNING! All changes made in this file will be lost when recompiling UI file!
********************************************************************************/

#ifndef UI_DIALOG_H
#define UI_DIALOG_H

#include <QtCore/QVariant>
#include <QtWidgets/QApplication>
#include <QtWidgets/QDialog>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QListWidget>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QTextBrowser>
#include <QtWidgets/QVBoxLayout>
#include <QtWidgets/QWidget>

QT_BEGIN_NAMESPACE

class Ui_Dialog
{
public:
    QWidget *horizontalLayoutWidget;
    QHBoxLayout *horizontalLayout_8;
    QVBoxLayout *verticalLayout_2;
    QHBoxLayout *horizontalLayout_6;
    QVBoxLayout *verticalLayout;
    QHBoxLayout *horizontalLayout_11;
    QLabel *label_2;
    QHBoxLayout *horizontalLayout_7;
    QLineEdit *lineEdit;
    QPushButton *submitline;
    QHBoxLayout *horizontalLayout_3;
    QPushButton *checkstatus;
    QLabel *statusLabel;
    QHBoxLayout *horizontalLayout;
    QSpacerItem *horizontalSpacer;
    QVBoxLayout *verticalLayout_4;
    QHBoxLayout *horizontalLayout_2;
    QLabel *label_5;
    QLineEdit *motor_settings;
    QPushButton *manualrun;
    QPushButton *stopMr;
    QSpacerItem *horizontalSpacer_2;
    QHBoxLayout *horizontalLayout_12;
    QPushButton *getFiles;
    QListWidget *filesWidget;
    QHBoxLayout *horizontalLayout_4;
    QPushButton *startPr;
    QPushButton *pausePr;
    QPushButton *stopPr;
    QPushButton *resumePr;
    QHBoxLayout *horizontalLayout_5;
    QVBoxLayout *verticalLayout_3;
    QHBoxLayout *horizontalLayout_9;
    QLabel *label;
    QLabel *label_3;
    QTextBrowser *textBrowser;
    QLabel *label_7;
    QLabel *label_8;
    QLabel *label_9;

    void setupUi(QDialog *Dialog)
    {
        if (Dialog->objectName().isEmpty())
            Dialog->setObjectName(QString::fromUtf8("Dialog"));
        Dialog->resize(1008, 578);
        horizontalLayoutWidget = new QWidget(Dialog);
        horizontalLayoutWidget->setObjectName(QString::fromUtf8("horizontalLayoutWidget"));
        horizontalLayoutWidget->setGeometry(QRect(10, 70, 991, 471));
        horizontalLayout_8 = new QHBoxLayout(horizontalLayoutWidget);
        horizontalLayout_8->setSpacing(6);
        horizontalLayout_8->setContentsMargins(11, 11, 11, 11);
        horizontalLayout_8->setObjectName(QString::fromUtf8("horizontalLayout_8"));
        horizontalLayout_8->setContentsMargins(0, 0, 0, 0);
        verticalLayout_2 = new QVBoxLayout();
        verticalLayout_2->setSpacing(6);
        verticalLayout_2->setObjectName(QString::fromUtf8("verticalLayout_2"));
        horizontalLayout_6 = new QHBoxLayout();
        horizontalLayout_6->setSpacing(6);
        horizontalLayout_6->setObjectName(QString::fromUtf8("horizontalLayout_6"));
        verticalLayout = new QVBoxLayout();
        verticalLayout->setSpacing(6);
        verticalLayout->setObjectName(QString::fromUtf8("verticalLayout"));
        horizontalLayout_11 = new QHBoxLayout();
        horizontalLayout_11->setSpacing(6);
        horizontalLayout_11->setObjectName(QString::fromUtf8("horizontalLayout_11"));

        verticalLayout->addLayout(horizontalLayout_11);

        label_2 = new QLabel(horizontalLayoutWidget);
        label_2->setObjectName(QString::fromUtf8("label_2"));

        verticalLayout->addWidget(label_2);

        horizontalLayout_7 = new QHBoxLayout();
        horizontalLayout_7->setSpacing(6);
        horizontalLayout_7->setObjectName(QString::fromUtf8("horizontalLayout_7"));
        lineEdit = new QLineEdit(horizontalLayoutWidget);
        lineEdit->setObjectName(QString::fromUtf8("lineEdit"));

        horizontalLayout_7->addWidget(lineEdit);

        submitline = new QPushButton(horizontalLayoutWidget);
        submitline->setObjectName(QString::fromUtf8("submitline"));

        horizontalLayout_7->addWidget(submitline);


        verticalLayout->addLayout(horizontalLayout_7);

        horizontalLayout_3 = new QHBoxLayout();
        horizontalLayout_3->setSpacing(6);
        horizontalLayout_3->setObjectName(QString::fromUtf8("horizontalLayout_3"));
        checkstatus = new QPushButton(horizontalLayoutWidget);
        checkstatus->setObjectName(QString::fromUtf8("checkstatus"));

        horizontalLayout_3->addWidget(checkstatus);

        statusLabel = new QLabel(horizontalLayoutWidget);
        statusLabel->setObjectName(QString::fromUtf8("statusLabel"));

        horizontalLayout_3->addWidget(statusLabel);


        verticalLayout->addLayout(horizontalLayout_3);


        horizontalLayout_6->addLayout(verticalLayout);


        verticalLayout_2->addLayout(horizontalLayout_6);

        horizontalLayout = new QHBoxLayout();
        horizontalLayout->setSpacing(6);
        horizontalLayout->setObjectName(QString::fromUtf8("horizontalLayout"));
        horizontalSpacer = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout->addItem(horizontalSpacer);

        verticalLayout_4 = new QVBoxLayout();
        verticalLayout_4->setSpacing(6);
        verticalLayout_4->setObjectName(QString::fromUtf8("verticalLayout_4"));

        horizontalLayout->addLayout(verticalLayout_4);


        verticalLayout_2->addLayout(horizontalLayout);

        horizontalLayout_2 = new QHBoxLayout();
        horizontalLayout_2->setSpacing(6);
        horizontalLayout_2->setObjectName(QString::fromUtf8("horizontalLayout_2"));
        label_5 = new QLabel(horizontalLayoutWidget);
        label_5->setObjectName(QString::fromUtf8("label_5"));

        horizontalLayout_2->addWidget(label_5);

        motor_settings = new QLineEdit(horizontalLayoutWidget);
        motor_settings->setObjectName(QString::fromUtf8("motor_settings"));
        motor_settings->setAutoFillBackground(false);

        horizontalLayout_2->addWidget(motor_settings);

        manualrun = new QPushButton(horizontalLayoutWidget);
        manualrun->setObjectName(QString::fromUtf8("manualrun"));

        horizontalLayout_2->addWidget(manualrun);

        stopMr = new QPushButton(horizontalLayoutWidget);
        stopMr->setObjectName(QString::fromUtf8("stopMr"));

        horizontalLayout_2->addWidget(stopMr);

        horizontalSpacer_2 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout_2->addItem(horizontalSpacer_2);


        verticalLayout_2->addLayout(horizontalLayout_2);

        horizontalLayout_12 = new QHBoxLayout();
        horizontalLayout_12->setSpacing(6);
        horizontalLayout_12->setObjectName(QString::fromUtf8("horizontalLayout_12"));
        getFiles = new QPushButton(horizontalLayoutWidget);
        getFiles->setObjectName(QString::fromUtf8("getFiles"));

        horizontalLayout_12->addWidget(getFiles);

        filesWidget = new QListWidget(horizontalLayoutWidget);
        filesWidget->setObjectName(QString::fromUtf8("filesWidget"));

        horizontalLayout_12->addWidget(filesWidget);


        verticalLayout_2->addLayout(horizontalLayout_12);

        horizontalLayout_4 = new QHBoxLayout();
        horizontalLayout_4->setSpacing(6);
        horizontalLayout_4->setObjectName(QString::fromUtf8("horizontalLayout_4"));
        startPr = new QPushButton(horizontalLayoutWidget);
        startPr->setObjectName(QString::fromUtf8("startPr"));

        horizontalLayout_4->addWidget(startPr);

        pausePr = new QPushButton(horizontalLayoutWidget);
        pausePr->setObjectName(QString::fromUtf8("pausePr"));

        horizontalLayout_4->addWidget(pausePr);

        stopPr = new QPushButton(horizontalLayoutWidget);
        stopPr->setObjectName(QString::fromUtf8("stopPr"));

        horizontalLayout_4->addWidget(stopPr);

        resumePr = new QPushButton(horizontalLayoutWidget);
        resumePr->setObjectName(QString::fromUtf8("resumePr"));

        horizontalLayout_4->addWidget(resumePr);


        verticalLayout_2->addLayout(horizontalLayout_4);

        horizontalLayout_5 = new QHBoxLayout();
        horizontalLayout_5->setSpacing(6);
        horizontalLayout_5->setObjectName(QString::fromUtf8("horizontalLayout_5"));

        verticalLayout_2->addLayout(horizontalLayout_5);


        horizontalLayout_8->addLayout(verticalLayout_2);

        verticalLayout_3 = new QVBoxLayout();
        verticalLayout_3->setSpacing(6);
        verticalLayout_3->setObjectName(QString::fromUtf8("verticalLayout_3"));
        horizontalLayout_9 = new QHBoxLayout();
        horizontalLayout_9->setSpacing(6);
        horizontalLayout_9->setObjectName(QString::fromUtf8("horizontalLayout_9"));
        label = new QLabel(horizontalLayoutWidget);
        label->setObjectName(QString::fromUtf8("label"));

        horizontalLayout_9->addWidget(label);

        label_3 = new QLabel(horizontalLayoutWidget);
        label_3->setObjectName(QString::fromUtf8("label_3"));
        label_3->setWordWrap(false);
        label_3->setOpenExternalLinks(true);

        horizontalLayout_9->addWidget(label_3);


        verticalLayout_3->addLayout(horizontalLayout_9);

        textBrowser = new QTextBrowser(horizontalLayoutWidget);
        textBrowser->setObjectName(QString::fromUtf8("textBrowser"));

        verticalLayout_3->addWidget(textBrowser);


        horizontalLayout_8->addLayout(verticalLayout_3);

        label_7 = new QLabel(Dialog);
        label_7->setObjectName(QString::fromUtf8("label_7"));
        label_7->setGeometry(QRect(10, 550, 561, 22));
        label_8 = new QLabel(Dialog);
        label_8->setObjectName(QString::fromUtf8("label_8"));
        label_8->setGeometry(QRect(20, 10, 81, 51));
        label_8->setPixmap(QPixmap(QString::fromUtf8("Picture1.png")));
        label_8->setScaledContents(true);
        label_9 = new QLabel(Dialog);
        label_9->setObjectName(QString::fromUtf8("label_9"));
        label_9->setGeometry(QRect(100, 10, 171, 51));
        label_9->setAutoFillBackground(false);
        label_9->setFrameShape(QFrame::NoFrame);
        label_9->setPixmap(QPixmap(QString::fromUtf8("Picture2.png")));
        label_9->setScaledContents(true);

        retranslateUi(Dialog);

        QMetaObject::connectSlotsByName(Dialog);
    } // setupUi

    void retranslateUi(QDialog *Dialog)
    {
        Dialog->setWindowTitle(QCoreApplication::translate("Dialog", "Photon Mono X Multi-Material Interface", nullptr));
        label_2->setText(QCoreApplication::translate("Dialog", "Enter Line with Material and Line Number:", nullptr));
        lineEdit->setPlaceholderText(QCoreApplication::translate("Dialog", "e.g., A,1:B,2", nullptr));
        submitline->setText(QCoreApplication::translate("Dialog", "Set", nullptr));
        checkstatus->setText(QCoreApplication::translate("Dialog", "Check Status", nullptr));
        statusLabel->setText(QCoreApplication::translate("Dialog", "Disconnected...", nullptr));
        label_5->setText(QCoreApplication::translate("Dialog", "Motor Control:", nullptr));
        motor_settings->setText(QString());
        motor_settings->setPlaceholderText(QCoreApplication::translate("Dialog", "e.g., A, F OR A, R", nullptr));
        manualrun->setText(QCoreApplication::translate("Dialog", "Motor Run", nullptr));
        stopMr->setText(QCoreApplication::translate("Dialog", "Pause Print", nullptr));
        getFiles->setText(QCoreApplication::translate("Dialog", "Get Files", nullptr));
        startPr->setText(QCoreApplication::translate("Dialog", "Begin MM", nullptr));
        pausePr->setText(QCoreApplication::translate("Dialog", "Pause", nullptr));
        stopPr->setText(QCoreApplication::translate("Dialog", "Stop Print", nullptr));
        resumePr->setText(QCoreApplication::translate("Dialog", "Resume", nullptr));
        label->setText(QCoreApplication::translate("Dialog", "Output:", nullptr));
        label_3->setText(QCoreApplication::translate("Dialog", "Continually polls the printer to control the printer (see the output box). ", nullptr));
        label_7->setText(QCoreApplication::translate("Dialog", "(2023) A Collaborative Project between Scion and Massey AgriFood Digital Lab ", nullptr));
        label_8->setText(QString());
        label_9->setText(QString());
    } // retranslateUi

};

namespace Ui {
    class Dialog: public Ui_Dialog {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_DIALOG_H

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
#include <QtWidgets/QGridLayout>
#include <QtWidgets/QHBoxLayout>
#include <QtWidgets/QLabel>
#include <QtWidgets/QLineEdit>
#include <QtWidgets/QListWidget>
#include <QtWidgets/QPushButton>
#include <QtWidgets/QSpacerItem>
#include <QtWidgets/QTextBrowser>
#include <QtWidgets/QVBoxLayout>

QT_BEGIN_NAMESPACE

class Ui_Dialog
{
public:
    QGridLayout *gridLayout;
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
    QPushButton *stopMM;
    QPushButton *pausePr;
    QPushButton *stopPr;
    QPushButton *resumePr;
    QHBoxLayout *horizontalLayout_5;
    QVBoxLayout *verticalLayout_3;
    QHBoxLayout *horizontalLayout_9;
    QLabel *label;
    QLabel *label_3;
    QTextBrowser *textBrowser;
    QHBoxLayout *horizontalLayout_10;
    QLabel *label_7;
    QSpacerItem *horizontalSpacer_3;
    QVBoxLayout *verticalLayout_5;
    QLabel *label_4;
    QLabel *label_6;
    QLabel *label_8;

    void setupUi(QDialog *Dialog)
    {
        if (Dialog->objectName().isEmpty())
            Dialog->setObjectName(QString::fromUtf8("Dialog"));
        Dialog->resize(929, 401);
        Dialog->setMaximumSize(QSize(1080, 720));
        Dialog->setBaseSize(QSize(1080, 720));
        gridLayout = new QGridLayout(Dialog);
        gridLayout->setSpacing(6);
        gridLayout->setContentsMargins(11, 11, 11, 11);
        gridLayout->setObjectName(QString::fromUtf8("gridLayout"));
        horizontalLayout_8 = new QHBoxLayout();
        horizontalLayout_8->setSpacing(6);
        horizontalLayout_8->setObjectName(QString::fromUtf8("horizontalLayout_8"));
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

        label_2 = new QLabel(Dialog);
        label_2->setObjectName(QString::fromUtf8("label_2"));

        verticalLayout->addWidget(label_2);

        horizontalLayout_7 = new QHBoxLayout();
        horizontalLayout_7->setSpacing(6);
        horizontalLayout_7->setObjectName(QString::fromUtf8("horizontalLayout_7"));
        lineEdit = new QLineEdit(Dialog);
        lineEdit->setObjectName(QString::fromUtf8("lineEdit"));

        horizontalLayout_7->addWidget(lineEdit);

        submitline = new QPushButton(Dialog);
        submitline->setObjectName(QString::fromUtf8("submitline"));

        horizontalLayout_7->addWidget(submitline);


        verticalLayout->addLayout(horizontalLayout_7);

        horizontalLayout_3 = new QHBoxLayout();
        horizontalLayout_3->setSpacing(6);
        horizontalLayout_3->setObjectName(QString::fromUtf8("horizontalLayout_3"));
        checkstatus = new QPushButton(Dialog);
        checkstatus->setObjectName(QString::fromUtf8("checkstatus"));

        horizontalLayout_3->addWidget(checkstatus);

        statusLabel = new QLabel(Dialog);
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
        label_5 = new QLabel(Dialog);
        label_5->setObjectName(QString::fromUtf8("label_5"));

        horizontalLayout_2->addWidget(label_5);

        motor_settings = new QLineEdit(Dialog);
        motor_settings->setObjectName(QString::fromUtf8("motor_settings"));
        motor_settings->setAutoFillBackground(false);

        horizontalLayout_2->addWidget(motor_settings);

        manualrun = new QPushButton(Dialog);
        manualrun->setObjectName(QString::fromUtf8("manualrun"));

        horizontalLayout_2->addWidget(manualrun);

        stopMr = new QPushButton(Dialog);
        stopMr->setObjectName(QString::fromUtf8("stopMr"));

        horizontalLayout_2->addWidget(stopMr);

        horizontalSpacer_2 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout_2->addItem(horizontalSpacer_2);


        verticalLayout_2->addLayout(horizontalLayout_2);

        horizontalLayout_12 = new QHBoxLayout();
        horizontalLayout_12->setSpacing(6);
        horizontalLayout_12->setObjectName(QString::fromUtf8("horizontalLayout_12"));
        getFiles = new QPushButton(Dialog);
        getFiles->setObjectName(QString::fromUtf8("getFiles"));

        horizontalLayout_12->addWidget(getFiles);

        filesWidget = new QListWidget(Dialog);
        filesWidget->setObjectName(QString::fromUtf8("filesWidget"));

        horizontalLayout_12->addWidget(filesWidget);


        verticalLayout_2->addLayout(horizontalLayout_12);

        horizontalLayout_4 = new QHBoxLayout();
        horizontalLayout_4->setSpacing(6);
        horizontalLayout_4->setObjectName(QString::fromUtf8("horizontalLayout_4"));
        startPr = new QPushButton(Dialog);
        startPr->setObjectName(QString::fromUtf8("startPr"));

        horizontalLayout_4->addWidget(startPr);

        stopMM = new QPushButton(Dialog);
        stopMM->setObjectName(QString::fromUtf8("stopMM"));

        horizontalLayout_4->addWidget(stopMM);

        pausePr = new QPushButton(Dialog);
        pausePr->setObjectName(QString::fromUtf8("pausePr"));

        horizontalLayout_4->addWidget(pausePr);

        stopPr = new QPushButton(Dialog);
        stopPr->setObjectName(QString::fromUtf8("stopPr"));

        horizontalLayout_4->addWidget(stopPr);

        resumePr = new QPushButton(Dialog);
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
        label = new QLabel(Dialog);
        label->setObjectName(QString::fromUtf8("label"));

        horizontalLayout_9->addWidget(label);

        label_3 = new QLabel(Dialog);
        label_3->setObjectName(QString::fromUtf8("label_3"));
        label_3->setWordWrap(false);
        label_3->setOpenExternalLinks(true);

        horizontalLayout_9->addWidget(label_3);


        verticalLayout_3->addLayout(horizontalLayout_9);

        textBrowser = new QTextBrowser(Dialog);
        textBrowser->setObjectName(QString::fromUtf8("textBrowser"));

        verticalLayout_3->addWidget(textBrowser);


        horizontalLayout_8->addLayout(verticalLayout_3);


        gridLayout->addLayout(horizontalLayout_8, 1, 0, 1, 1);

        horizontalLayout_10 = new QHBoxLayout();
        horizontalLayout_10->setSpacing(6);
        horizontalLayout_10->setObjectName(QString::fromUtf8("horizontalLayout_10"));
        label_7 = new QLabel(Dialog);
        label_7->setObjectName(QString::fromUtf8("label_7"));

        horizontalLayout_10->addWidget(label_7);

        horizontalSpacer_3 = new QSpacerItem(40, 20, QSizePolicy::Expanding, QSizePolicy::Minimum);

        horizontalLayout_10->addItem(horizontalSpacer_3);

        verticalLayout_5 = new QVBoxLayout();
        verticalLayout_5->setSpacing(6);
        verticalLayout_5->setObjectName(QString::fromUtf8("verticalLayout_5"));
        label_4 = new QLabel(Dialog);
        label_4->setObjectName(QString::fromUtf8("label_4"));

        verticalLayout_5->addWidget(label_4);

        label_6 = new QLabel(Dialog);
        label_6->setObjectName(QString::fromUtf8("label_6"));

        verticalLayout_5->addWidget(label_6);


        horizontalLayout_10->addLayout(verticalLayout_5);


        gridLayout->addLayout(horizontalLayout_10, 2, 0, 1, 1);

        label_8 = new QLabel(Dialog);
        label_8->setObjectName(QString::fromUtf8("label_8"));
        QPalette palette;
        QBrush brush(QColor(0, 0, 0, 255));
        brush.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::WindowText, brush);
        QBrush brush1(QColor(147, 200, 151, 255));
        brush1.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::Button, brush1);
        QBrush brush2(QColor(232, 255, 234, 255));
        brush2.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::Light, brush2);
        QBrush brush3(QColor(189, 227, 192, 255));
        brush3.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::Midlight, brush3);
        QBrush brush4(QColor(73, 100, 76, 255));
        brush4.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::Dark, brush4);
        QBrush brush5(QColor(98, 133, 101, 255));
        brush5.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::Mid, brush5);
        palette.setBrush(QPalette::Active, QPalette::Text, brush);
        QBrush brush6(QColor(255, 255, 255, 255));
        brush6.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::BrightText, brush6);
        palette.setBrush(QPalette::Active, QPalette::ButtonText, brush);
        palette.setBrush(QPalette::Active, QPalette::Base, brush6);
        palette.setBrush(QPalette::Active, QPalette::Window, brush1);
        palette.setBrush(QPalette::Active, QPalette::Shadow, brush);
        QBrush brush7(QColor(201, 227, 203, 255));
        brush7.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::AlternateBase, brush7);
        QBrush brush8(QColor(255, 255, 220, 255));
        brush8.setStyle(Qt::SolidPattern);
        palette.setBrush(QPalette::Active, QPalette::ToolTipBase, brush8);
        palette.setBrush(QPalette::Active, QPalette::ToolTipText, brush);
        QBrush brush9(QColor(0, 0, 0, 128));
        brush9.setStyle(Qt::SolidPattern);
#if QT_VERSION >= QT_VERSION_CHECK(5, 12, 0)
        palette.setBrush(QPalette::Active, QPalette::PlaceholderText, brush9);
#endif
        palette.setBrush(QPalette::Inactive, QPalette::WindowText, brush);
        palette.setBrush(QPalette::Inactive, QPalette::Button, brush1);
        palette.setBrush(QPalette::Inactive, QPalette::Light, brush2);
        palette.setBrush(QPalette::Inactive, QPalette::Midlight, brush3);
        palette.setBrush(QPalette::Inactive, QPalette::Dark, brush4);
        palette.setBrush(QPalette::Inactive, QPalette::Mid, brush5);
        palette.setBrush(QPalette::Inactive, QPalette::Text, brush);
        palette.setBrush(QPalette::Inactive, QPalette::BrightText, brush6);
        palette.setBrush(QPalette::Inactive, QPalette::ButtonText, brush);
        palette.setBrush(QPalette::Inactive, QPalette::Base, brush6);
        palette.setBrush(QPalette::Inactive, QPalette::Window, brush1);
        palette.setBrush(QPalette::Inactive, QPalette::Shadow, brush);
        palette.setBrush(QPalette::Inactive, QPalette::AlternateBase, brush7);
        palette.setBrush(QPalette::Inactive, QPalette::ToolTipBase, brush8);
        palette.setBrush(QPalette::Inactive, QPalette::ToolTipText, brush);
#if QT_VERSION >= QT_VERSION_CHECK(5, 12, 0)
        palette.setBrush(QPalette::Inactive, QPalette::PlaceholderText, brush9);
#endif
        palette.setBrush(QPalette::Disabled, QPalette::WindowText, brush4);
        palette.setBrush(QPalette::Disabled, QPalette::Button, brush1);
        palette.setBrush(QPalette::Disabled, QPalette::Light, brush2);
        palette.setBrush(QPalette::Disabled, QPalette::Midlight, brush3);
        palette.setBrush(QPalette::Disabled, QPalette::Dark, brush4);
        palette.setBrush(QPalette::Disabled, QPalette::Mid, brush5);
        palette.setBrush(QPalette::Disabled, QPalette::Text, brush4);
        palette.setBrush(QPalette::Disabled, QPalette::BrightText, brush6);
        palette.setBrush(QPalette::Disabled, QPalette::ButtonText, brush4);
        palette.setBrush(QPalette::Disabled, QPalette::Base, brush1);
        palette.setBrush(QPalette::Disabled, QPalette::Window, brush1);
        palette.setBrush(QPalette::Disabled, QPalette::Shadow, brush);
        palette.setBrush(QPalette::Disabled, QPalette::AlternateBase, brush1);
        palette.setBrush(QPalette::Disabled, QPalette::ToolTipBase, brush8);
        palette.setBrush(QPalette::Disabled, QPalette::ToolTipText, brush);
#if QT_VERSION >= QT_VERSION_CHECK(5, 12, 0)
        palette.setBrush(QPalette::Disabled, QPalette::PlaceholderText, brush9);
#endif
        label_8->setPalette(palette);
        QFont font;
        font.setPointSize(20);
        font.setBold(true);
        font.setWeight(75);
        label_8->setFont(font);
        label_8->setFrameShape(QFrame::WinPanel);
        label_8->setFrameShadow(QFrame::Raised);
        label_8->setLineWidth(1);
        label_8->setScaledContents(false);
        label_8->setAlignment(Qt::AlignCenter);

        gridLayout->addWidget(label_8, 0, 0, 1, 1);


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
        stopMr->setText(QCoreApplication::translate("Dialog", "Motor Stop", nullptr));
        getFiles->setText(QCoreApplication::translate("Dialog", "Get Files", nullptr));
        startPr->setText(QCoreApplication::translate("Dialog", "Begin MM", nullptr));
        stopMM->setText(QCoreApplication::translate("Dialog", "Stop MM", nullptr));
        pausePr->setText(QCoreApplication::translate("Dialog", "Pause Printer", nullptr));
        stopPr->setText(QCoreApplication::translate("Dialog", "Stop Printer", nullptr));
        resumePr->setText(QCoreApplication::translate("Dialog", "Resume Printer", nullptr));
        label->setText(QCoreApplication::translate("Dialog", "Output:", nullptr));
        label_3->setText(QCoreApplication::translate("Dialog", "Continually polls the printer to control the printer (see the output box). ", nullptr));
        label_7->setText(QCoreApplication::translate("Dialog", "(2023) A Collaborative Project between Scion and Massey AgriFood Digital Lab ", nullptr));
        label_4->setText(QCoreApplication::translate("Dialog", "Author: JH Odendaal", nullptr));
        label_6->setText(QCoreApplication::translate("Dialog", "Email: jh.odendaal@outlook.com", nullptr));
        label_8->setText(QCoreApplication::translate("Dialog", "Scion Multi-Material Anycubic Photon Mono X 6k Control Interface", nullptr));
    } // retranslateUi

};

namespace Ui {
    class Dialog: public Ui_Dialog {};
} // namespace Ui

QT_END_NAMESPACE

#endif // UI_DIALOG_H

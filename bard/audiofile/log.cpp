/*
    This file is part of Bard (https://github.com/antlarr/bard)
    Copyright (C) 2024 Antonio Larrosa <antonio.larrosa@gmail.com>

    Bard is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, version 3.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/
#include "log.h"
#include <array>
#include <string>
#include <vector>
#include <stdlib.h>
#include <sstream>

#ifdef DEBUG
int current_log_level = 0;
#endif

std::array<bool, LogArea::LastArea> current_areas_states;

using std::string;
using std::vector;

vector <string> split(const string &s, char sep)
{
    std::stringstream ss(s);
    string str;
    vector<string> v;

    while (getline(ss, str, sep))
        v.push_back(str);

    return v;
}

void initLog()
{
    const char * areas = secure_getenv("AUDIOFILE_LOG_AREAS");
    if (!areas)
       return;

    auto tokens = split(string(areas), ',');

    for (const string &token: tokens)
    {
        if (token == "*")
        {

            for (int i = 0; i < static_cast<int>(LogArea::LastArea); ++i)
                current_areas_states[i] = true;
            break;
        }
        size_t idx;
        long v;
        bool ok = true;
        try {
            v = std::stol(token.c_str(), &idx, 10);
        } catch (std::invalid_argument) {
            ok = false;
        }
        if (!ok || idx != token.length())
        {
            std::cerr << "Invalid area " << token << std::endl;
            continue;
        }
        current_areas_states[v] = true;
    }
}

std::ostream &logDebug(LogArea area)
{
#ifdef DEBUG
    if (current_areas_states[area])
        return std::cout;
#endif
    static std::ostream nullstream{nullptr};
    return nullstream;
}

void setLogLevel(LogLevel level)
{
    current_log_level = level;
}

void setLogAreaState(LogArea area, bool enable)
{
    current_areas_states[area] = enable;
}

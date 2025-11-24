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

const string &logAreaName(LogArea area)
{
    return s_logAreas.at(area);
}

LogArea logAreaByName(const string &name, bool *found=nullptr)
{
    for (const auto &it: s_logAreas)
    {
        if (it.second == name)
        {
            if (found)
                *found=true;
            return it.first;
        }
    }
    if (found)
        *found=false;
    return Default;
}

vector <string> split(const string &s, char sep)
{
    std::stringstream ss(s);
    string str;
    vector<string> v;

    while (getline(ss, str, sep))
        v.push_back(str);

    return v;
}

bool check_s_logAreas_integrity()
{
    return s_logAreas.size() == LastArea;
}

void initLog()
{
    if (!check_s_logAreas_integrity())
        std::cerr << "Error: s_logAreas map needs to be updated (has " << s_logAreas.size()
                  << " elements but the LogAreas enum has " << (int)LastArea << " elements)" << std::endl;

    const char * areas = secure_getenv("AUDIOFILE_LOG_AREAS");
    if (!areas)
       return;

    auto tokens = split(string(areas), ',');
    bool found = false;

    for (const string &token: tokens)
    {
        if (token == "*")
        {

            for (int i = 0; i < static_cast<int>(LogArea::LastArea); ++i)
                current_areas_states[i] = true;
            break;
        }
        long v = logAreaByName(token, &found);
        if (found)
        {
            current_areas_states[v] = true;
            break;
        }

        size_t idx;
        bool ok = true;
        try {
            v = std::stol(token.c_str(), &idx, 10);
        } catch (std::invalid_argument &) {
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
#ifdef DEBUG
    current_log_level = level;
#endif
}

void setLogAreaState(LogArea area, bool enable)
{
    current_areas_states[area] = enable;
}
